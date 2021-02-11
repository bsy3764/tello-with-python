# droneapp/models/drone_manage.py

import logging
import socket
import time
import threading  # 드론 상태 메시지 받기 위해
import contextlib  # 드론 순찰시키기
from droneapp.models.base import Singleton  # 싱글톤
import os
import subprocess   # 자식 프로세스를 생성하고, 필요하다면 입출력을 주고받을 수 있게 해줌
import cv2
import numpy as np
import math
from DJITelloPy.djitellopy import tello
import droneapp.models.KeyPress_Module as kp

logger = logging.getLogger(__name__)    # getLogger의 인자로는 만들고 싶은 로거 이름을 전달

##############드론 제어###############
DEFAULT_DISTANCE = 0.30  # 기본 드론 움직이는 거리
DEFAULT_SPEED = 10  # 기본 드론 스피드 설정
DEFAULT_DEGREE = 15    # 기본 각도
#####################################

##############드론 사진###############
FRAME_X = int(960 / 3)  # 프레임의 높이
FRAME_Y = int(720 / 3)  # 프레임의 넓이
FRAME_CENTER_X = FRAME_X / 2    # 프레임의 정가운데 X좌표
FRAME_CENTER_Y = FRAME_Y / 2    # 프레임의 정가운데 Y좌표
FRAME_AREA = FRAME_X * FRAME_Y  # 프레임의 면적
FRAME_SIZE = FRAME_AREA * 3     # 프레임의 크기(컬러 필터 3개)
#####################################

# ffmpeg : 오픈소스 기반의 영상 인코더
# -hwaccel : 하드웨어 가속을 사용하여 일치하는 스트림을 디코딩
# auto : 하드웨어 가속 방법 자동 선택
# -hwaccel_device : 하드웨어 가속에 사용할 디바이스 선택, 이 옵션은 -hwacel 옵션도 지정된 경우에만 의미가 있음
# -pix_fmt : 픽셀 형식을 설정
# rawvideo : Raw video decoder
CMD_FFMPEG = f'ffmpeg -hwaccel auto -hwaccel_device opencl -i pipe:0 ' \
             f'-pix_fmt bgr24 -s {FRAME_X}x{FRAME_Y} -f rawvideo pipe:1'

# 스냅샷의 저장 경로
SNAPSHOT_IMAGE_FOLDER = './droneapp/static/img/snapshots/'

# 스냅샷의 저장경로가 있는지 체크하는 클래스
class ErrorNoImageDir(Exception):
    """Error no snapshot image dir"""

# is_imperial : ft(피트)란 단위를 안쓰면 False, 사용하면 True
class DroneManager(metaclass=Singleton):    # 싱글톤 사용하기
    def __init__(self, host_ip='192.168.10.2', host_port=8889,
                 drone_ip='192.168.10.1', drone_port=8889, status_port=8890,
                 is_imperial=False, speed=DEFAULT_SPEED):
        self.host_ip = host_ip
        self.host_port = host_port
        self.drone_ip = drone_ip
        self.drone_port = drone_port
        self.status_port = status_port
        self.drone_address = (drone_ip, drone_port)
        self.is_imperial = is_imperial
        self.speed = speed

        # 소켓 생성
        # UDP이므로 SOCK_DGRAM 사용
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 소켓에 주소, 포트 할당
        self.socket.bind((self.host_ip, self.host_port))

        # 드론의 상태 메시지
        self.response = None  # 변수 None으로 초기화
        self.stop_event = threading.Event()  # 상태 메시지를 그만 받을 준비(대기 상태)
        # 이벤트 객체 생성(default flag = 0)
        # 하나 이상의 쓰레드가 이벤트를 기다리고 있다가, 누군가가 시그널을 주면 일제히 동작을 시작

        # Thread 객체를 얻음, 함수 및 메서드 실행 방식
        self._response_thread = threading.Thread(target=self.receive_response,
                args=(self.stop_event,))
        self._response_thread.start()  # 쓰레드 시작(병렬 처리 시작)

        # 순찰관련 이벤트 변수 초기화
        self.patrol_event = None

       # 순찰 실행 여부 판단할 변수
        self.is_patrol = False

        # 상호배제를 하면서 동시에 수행할 수 있는 스레드의 개수를 설정
        # 생성자를 이용해서 동시 수행가능한 개수를 설정
        # Semaphore : Lock이라는 키를 여러 개 가질 수 있음
        self._patrol_semaphore = threading.Semaphore(1)  # 순찰을 담당하는 쓰레드 1개를 관리하는 세마포어

        self._thread_patrol = None

        # ffmpeg을 실행
        # 상호작용을 위해서는 subprocess.Popen()으로 자식 프로세스를 시작하고,
        # 필요한 스트림(stdin, stdout)마다 subprocess.PIPE를 넣어줌
        self.proc = subprocess.Popen(CMD_FFMPEG.split(' '),  # 리스트로 반환해야 함
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE)

        # 다른 쓰레드에서 보내기 위해???
        self.proc_stdin = self.proc.stdin
        self.proc_stdout = self.proc.stdout

        # Vedio 스트림 포트
        self.video_port = 11111

        # Thread 객체를 얻음, 함수 및 메서드 실행 방식
        self._recive_video_thread = threading.Thread(
            target=self._recive_video,
            args=(self.stop_event, self.proc_stdin,
                  self.host_ip, self.video_port,)
        )
        self._recive_video_thread.start()   # 쓰레드 시작(병렬 처리 시작)

        if not os.path.exists(SNAPSHOT_IMAGE_FOLDER):   # 스냅샷 저장경로가 없다면
            raise ErrorNoImageDir(f'{SNAPSHOT_IMAGE_FOLDER} dose not exists')
        self.is_snapshot = False

        # 드론에게 명령어가 1개만 보내지도록(나머지는 대기 또는 skip)
        self._command_semaphore = threading.Semaphore(1)
        self._command_thread = None

        # 데이터 보내기(드론에게 명령어 전달)
        self.send_command('command')
        self.send_command('streamon')

        # 드론의 스피드 조절하는 함수 호출
        self.set_speed(self.speed)

    # 드론의 상태 메시지 받는 함수
    def receive_response(self, stop_event):
        while not stop_event.is_set():  # stop_event가 이벤트가 오기 전까지 반복
            try:
                # 소켓으로부터 데이터를 수신하고, 관련된 주소 및 포트 번호를 반환, flag의 상태 반환
                self.response, ip = self.socket.recvfrom(3000)  # 버퍼 사이즈를 3000
                logger.info({'action': 'receive_response', 'response': self.response})
            except socket.error as ex:
                logger.error({'action': 'receive_response', 'ex': ex})
                break

    def __dell__(self):
        self.stop()  # stop함수 호출

    def stop(self):
        self.stop_event.set()  # 이벤트를 설정(flag = 1 로 변경)

        # 쓰레드에서 메시지를 보내려는데, 이미 close한 소켓으로 인하여 에러 메시지 발생
        # 메시지를 다 받을 때 까지는 잠시 대기하게 만들기
        retry = 0
        while self._response_thread.isAlive():  # 쓰레드가 살아 있다면
            time.sleep(0.3)  # 0.3초 대기
            if retry > 30:  # 0.3초씩 대기를 30번 넘게 한다면
                break
            retry += 1

        self.socket.close()  # 소켓 연결을 닫고 연결된 리소스를 모두 해제
        os.kill(self.proc.pid, 9)   # 드론의 영상관련 프로세스 죽이기
        # Windows OS일 경우
        # import signal
        # os.kill(self.proc.pid, signal.CTRL_C_EVENT)

    # 명령어 전달 하는 함수
    def send_command(self, command, blocking=True):
        self._command_thread = threading.Thread(
            target=self._send_command,
            args=(command, blocking,)
        )
        self._command_thread.start()

    def _send_command(self, command, blocking=True):
        is_acquire = self._command_semaphore.acquire(blocking=blocking)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self._command_semaphore.release)
                logger.info({'action': 'send_command', 'command': command})  # 전달하는 명령어를 로그로 남기기
                self.socket.sendto(command.encode('utf-8'), self.drone_address)  # 소켓에 명령어가 문자열로 오므로 인코딩 필요

                # 메시지를 다 받을 때 까지는 잠시 대기하게 만들기
                retry = 0
                while self.response is None:    # is : 변수가 같은 Object(객체)를 가리키면 True
                    time.sleep(0.3)
                    if retry > 3:
                        break
                    retry += 1

                if self.response is None:
                    response = None
                else:
                    response = self.response.decode('utf-8')

                self.response = None
                return response
        else:
            logger.warning({'action': 'send_command', 'command': command, 'status': 'not_acquire'})

    def takeoff(self):
        return self.send_command('takeoff')  # takeoff란 문자열을 send_command함수에 전달

    def land(self):
        return self.send_command('land')

    # 드론 방향, 이동거리 설정하여 이동시키기
    def move(self, direction, distance):  # 방향과 이동거리 전달받는 함수
        distance = float(distance)
        if self.is_imperial:  # ft(피트)단위를 사용한다면
            distance = int(round(distance * 30.48))  # ft 단위로 환산하기
        else:
            distance = int(round(direction * 100))  # cm 단위로 환산하기
        return self.send_command(f'{direction} {distance}')
        # return self.send_command('{0} {1}'.format(direction, distance))

    def up(self, distance=DEFAULT_DISTANCE):
        return self.move('up', distance)

    def down(self, distance=DEFAULT_DISTANCE):
        return self.move('down', distance)

    def left(self, distance=DEFAULT_DISTANCE):
        return self.move('left', distance)

    def right(self, distance=DEFAULT_DISTANCE):
        return self.move('right', distance)

    def forward(self, distance=DEFAULT_DISTANCE):
        return self.move('forward', distance)

    def back(self, distance=DEFAULT_DISTANCE):
        return self.move('back', distance)

    def set_speed(self, speed):
        return self.send_command(f'speed {speed}')

    def clockwise(self, degree=DEFAULT_DEGREE):
        return self.send_command(f'cw {degree}')

    def counter_clockwise(self, degree=DEFAULT_DEGREE):
        return self.send_command(f'ccw {degree}')

    def flip_front(self):
        return self.send_command('flip f')

    def flip_back(self):
        return self.send_command('flip b')

    def flip_left(self):
        return self.send_command('flip l')

    def flip_right(self):
        return self.send_command('flip r')

    # 순찰을 시작하는 함수
    def patrol(self):
        if not self.is_patrol:
            self.patrol_event = threading.Event()   # 이벤트 객체 생성(default flag = 0)

            # Thread 객체를 얻음, 함수 및 메서드 실행 방식
            self._thread_patrol = threading.Thread(target=self._patrol,
                                    args=(self._patrol_semaphore, self.patrol_event))
            self._thread_patrol.start()  # 쓰레드 시작(병렬 처리 시작)
            self.is_patrol = True

    # 순찰을 멈추는 함수
    def stop_patrol(self):
        if self.is_patrol:
            self.patrol_event.set()  # 이벤트를 설정(flag = 1 로 변경)
            retry = 0
            while self._thread_patrol.isAlive():
                time.sleep(0.3)
                if retry > 300:
                    break
                retry += 1
            self.is_patrol = False

    def _patrol(self, semaphore, stop_event):
        # acquire : 리소스를 확보하는 메서드
        # lock을 가지고 있을 때만 공유 데이터에 접근이 가능
        is_acquire = semaphore.acquire(blocking=False)  # lock을 획득하려 시도하고 즉시 결과를 리턴
        if is_acquire:
            logger.info({'action': '_patrol', 'status': 'acquire'})

            # contextlib.ExitStack()
            # 다른 컨텍스트 관리자와 정리 함수, 특히 입력 데이터에 의해 선택적이거나
            # 다른 방식으로 구동되는 것들을 프로그래밍 방식으로 쉽게 결합할 수 있도록 설계된 컨텍스트 관리자
            # 각 인스턴스는 인스턴스가 닫힐 때, 역순으로 호출되는 등록된 콜백의 스택을 유지
            with contextlib.ExitStack() as stack:
                stack.callback(semaphore.release)   # release : 리소스를 해제하는 메서드
                status = 0
                while not stop_event.is_set():  # 순찰을 멈추는 이벤트가 오기 전까지
                    status += 1
                    if status == 1:
                        self.up()
                    if status == 2:
                        self.clockwise(90)
                    if status == 3:
                        self.down()
                    if status == 4:
                        status = 0
                    time.sleep(5)
        else:
            logger.warning({'action': '_patrol', 'status': 'not acquire'})

    # 드론이 보내는 영상을 받는 함수
    # pipe_in : self.proc_stdin
    def recive_video(self, stop_event, pipe_in, host_ip, video_port):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock_video:    # 소켓 생성
            sock_video.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    # 소켓옵션값을 변경
            sock_video.settimeout(.5)   # 블로킹 소켓 연산에 시간제한을 설정
            sock_video.bind((host_ip, video_port))
            data = bytearray(2048)
            while not stop_event.is_set():
                try:
                    size, addr = sock_video.recvfrom_into(data)  # 소켓에서 데이터를 얻어 버퍼에 씀
                    # logger.info({'action': 'receive_video', 'data': data})
                except socket.timeout as ex:    # timeout 에러가 발생하면
                    logger.warning({'action': 'receive_video', 'ex': ex})
                    time.sleep(0.5)   # 0.5초 대기
                    continue
                except socket.error as ex:      # socket error가 발생하면
                    logger.error({'action': 'receive_video', 'ex': ex})
                    break

                try:
                    # 자식 프로세스에 입력을 보낼 때 write()후 꼭 flush()를 호출.
                    # 입력이 버퍼에 남아 자식으로 가지 않은 경우가 발생하기 때문.
                    pipe_in.write(data[:size])
                    pipe_in.flush()
                except Exception as ex:
                    logger.warning({'action': 'receive_video', 'ex': ex})
                    break

    def video_binary_generator(self):
        while True:
            try:
                # 드론에서 찍은 영상을 ffmpeg으로 pipe0으로 전달한 것을 읽어오기
                frame = self.proc_stdout.read(FRAME_SIZE)
            except Exception as ex:
                logger.warning({'action': 'video_binary_generator', 'ex': ex})
                continue

            if not frame:
                continue

            # ffmpeg -> opencv 변경
            # binary를 배열로 변환
            frame = np.fromstring(frame, np.unit8).reshape(FRAME_Y, FRAME_X, 3)
            yield frame

    def enable_face_detect(self):   # face detect를 한다면
        self._is_enable_face_detect = True

    def disable_Face_detect(self):  # face detect를 안 한다면
        self._is_enable_face_detect = False

    # 드론에서 받은 영상을 web에서 보기위한 변환 함수
    def video_jpeg_generator(self):
        for frame in self.video_binary_generator():
            if self._is_enable_face_detect:
                if self.is_patrol:
                    self.stop_patrol()

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)    # 얼굴에 파란 사각형 표시

                    face_center_x = x + (w / 2)     # 얼굴로 인식한 부분의 가운데 x좌표
                    face_center_y = y + (h / 2)     # 얼굴로 인식한 부분의 가운데 y좌표
                    diff_x = FRAME_CENTER_X - face_center_x     # 화면의 정 가운데와 얼굴의 가운데의 x좌표 차이
                    diff_y = FRAME_CENTER_Y - face_center_y     # 화면의 정 가운데와 얼굴의 가운데의 y좌표 차이
                    face_area = w * h   # 얼굴로 인식한 사각형의 면적
                    percent_face = face_area / FRAME_AREA   # 전체 화면에서 얼굴의 비율(크기)

                    # 변수 초기화
                    drone_X, drone_y, drone_z, speed = 0, 0, 0, self.speed

                    # 드론이 얼굴을 무작정 따라가는 것이 아니라 특정 거리만큼 중앙에서 벗어날 경우 드론을 움직임
                    if diff_x < -30:
                        drone_y = -30
                    if diff_x > 30:
                        drone_y = 30
                    if diff_y < -15:
                        drone_z = -30
                    if diff_y > 15:
                        drone_z = 30
                    if percent_face > 0.30:
                        drone_X = -30
                    if percent_face < 0.02:
                        drone_X = 30
                    self.send_command(f'go {drone_X} {drone_y} {drone_z} {speed}',
                                      blocking=False)
                    break

            _, jpeg = cv2.imencode('.jpg', frame)
            jpeg_binary = jpeg.tobytes()  # web에서 영상을 보여주기 위해

            if self.is_snapshot:
                backup_file = time.strftime("%Y%m%d-%H%M%S") + '.jpg'
                snapshot_file = 'snapshot.jpg'
                for filename in (backup_file, snapshot_file):
                    file_path = os.path.join(SNAPSHOT_IMAGE_FOLDER, filename)
                    with open(file_path, 'wb') as f:
                        f.write(jpeg_binary)
                self.is_snapshot = False

            yield jpeg_binary   # 함수가 제너레이터를 반환

    # 스냅샷을 가져오기 위한 함수
    def snapshot(self):
        self.is_snapshot = True
        retry = 0
        while retry < 3:
            if not self.is_snapshot:
                return True
            time.sleep(0.1)
            retry += 1
        return False