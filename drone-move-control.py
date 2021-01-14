import logging
import socket
import sys
import time
import threading  # 드론 상태 메시지 받기 위해
import contextlib  # 드론 순찰시키기

logging.basicConfig(level=logging.INFO, stream=sys.stdout)  # 로깅 레벨을 설정
logger = logging.getLogger(__name__)    # getLogger의 인자로는 만들고 싶은 로거 이름을 전달

DEFAULT_DISTANCE = 0.30  # 30cm
DEFAULT_SPEED = 10  # 기본 드론 스피드 설정
DEFAULT_DEGREE = 15    # 기본 각도

# is_imperial : ft(피트)란 단위를 안쓰면 False, 사용하면 True
class DroneManager(object):
    def __init__(self, host_ip='192.168.10.2', host_port=8889,
                 drone_ip='192.168.10.1', drone_port=8889,
                 is_imperial=False, speed=DEFAULT_SPEED):
        self.host_ip = host_ip
        self.host_port = host_port
        self.drone_ip = drone_ip
        self.drone_port = drone_port
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

    # 명령어 전달 하는 함수
    def send_command(self, command):
        logger.info({'action': 'send_command', 'command': command})  # 전달하는 명령어를 로그로 남기기
        self.socket.sendto(command.encode('utf-8'), self.drone_address) # 소켓에 명령어가 문자열로 오므로 인코딩 필요

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

    # 순찰(어느 행동들을 진행할지 정의) 행동 정의
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

# __name__ : 모듈의 이름이 저장되는 변수
if __name__ == '__main__':  # 해당 파이썬 파일이 프로그램의 시작점이 맞는지 판단하는 작업
    drone_manager = DroneManager()

    drone_manager.patrol()
    time.sleep(45)
    drone_manager.stop_patrol()
    time.sleep(5)

    drone_manager.land()
    drone_manager.stop()