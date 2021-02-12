# coding=utf-8
import logging
import socket
import time
import threading
import cv2  # type: ignore
from threading import Thread
from typing import Optional   # None이 허용되는 함수의 매개 변수에 대한 타입을 명시할 때 유용
from DJITelloPy.djitellopy import enforce_types

threads_initialized = False
drones: Optional[dict] = {}     # drones변수는 type이 dict 또는 None이 할당될 수 있음, 빈 dict 생성
client_socket: socket.socket    # client_socket 변수는 type이 socket.socket

@enforce_types
class Tello:
    RESPONSE_TIMEOUT = 7  # 최대 응답 대기 시간(7초)
    TIME_BTW_COMMANDS = 0.1  # 매우 연속적인 명령어는 드론이 응답하지 않으므로 최소의 대기할 시간(sec)
    TIME_BTW_RC_CONTROL_COMMANDS = 0.001  # in seconds
    RETRY_COUNT = 3  # 명령어가 실패시 재시도하는 횟수
    TELLO_IP = '192.168.10.1'  # Tello IP주소

    # Video stream, server socket(컴퓨터)
    VS_UDP_IP = '0.0.0.0'
    VS_UDP_PORT = 11111			# 스트림(비디오) 포트

    CONTROL_UDP_PORT = 8889		# 명령어(command) 포트
    STATE_UDP_PORT = 8890		# 상태(state) 포트

    # logger 설정하기
    HANDLER = logging.StreamHandler()   # StreamHandler 클래스(로깅 출력)의 새로운 인스턴스를 반환
    FORMATTER = logging.Formatter('[%(levelname)s] %(filename)s - %(lineno)d - %(message)s')    # 로그 형태 지정
    HANDLER.setFormatter(FORMATTER)     # 지정한 로그 형태로 로그 출력하기

    LOGGER = logging.getLogger('djitellopy')    # 지정된 이름(djitellopy)의 로거 반환
    LOGGER.addHandler(HANDLER)  # 지정된 로거(HANDLER)를 이 로거에 추가
    LOGGER.setLevel(logging.INFO)   # 로깅 레벨(INFO) 지정

    # Tello 드론의 내장 센서의 상태들의 변수:자료형 형태의 dict로 정의(총 20개)
    state_field_converters = {
        # Tello EDU 미션패드 활셩화일 경우에만
        'mid': int,
        'x': int,
        'y': int,
        'z': int,
        # 'mpry': (custom format 'x,y,z')

        # 공통 항목
        'pitch': int,
        'roll': int,
        'yaw': int,
        'vgx': int,
        'vgy': int,
        'vgz': int,
        'templ': int,
        'temph': int,
        'tof': int,
        'h': int,
        'bat': int,
        'baro': float,
        'time': int,
        'agx': float,
        'agy': float,
        'agz': float,
    }

    # VideoCapture 객체
    cap: Optional[cv2.VideoCapture] = None  # cap이란 변수는 type이 cv2.VideoCapture 또는 None을 가짐
    background_frame_read: Optional['BackgroundFrameRead'] = None   # background_frame_read란 변수는 type이 BackgroundFrameRead 또는 None을 가짐

    stream_on = False   # 드론이 스트림을 틀고 있는지 여부 체크
    is_flying = False   # 드론이 날고 있는지 여부 체크

    def __init__(self, host=TELLO_IP, retry_count=RETRY_COUNT):
        # 글로벌 변수 지정하기
        global threads_initialized, client_socket, drones

        self.address = (host, Tello.CONTROL_UDP_PORT)   # 드론의 IP와 command를 전달할 Port
        self.stream_on = False
        self.retry_count = retry_count
        self.last_received_command_timestamp = time.time()      # 현재 시각 반환
        self.last_rc_control_timestamp = time.time()        # 현재 시각 반환

        # threads_initialized 초기화를 False로 해놓음
        if not threads_initialized:    # threads_initialized가 False라면(처음 실행한다면)
            # 백그라운드에서 udp_response_receiver, udp_state_receiver 함수를 실행시킴

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    # client_socket 소켓 생성
            client_socket.bind(('', Tello.CONTROL_UDP_PORT))    # 서버의 IP와 Post 고정
            # udp_response_receiver 함수(드론의 응답을 받는 함수)를 병렬로 처리할 예정
            response_receiver_thread = threading.Thread(target=Tello.udp_response_receiver)
            # 서브쓰레드가 데몬 쓰레드인지 아닌지를 지정
            # 데몬 쓰레드란 백그라운드에서 실행되는 쓰레드로 메인 쓰레드가 종료되면 즉시 종료되는 쓰레드
            response_receiver_thread.daemon = True  # 데몬 쓰레드로 지정
            response_receiver_thread.start()    # 병렬처리 시작

            # udp_state_receiver 함수(드론의 상태정보를 받는 함수)를 병렬로 처리할 예정
            state_receiver_thread = threading.Thread(target=Tello.udp_state_receiver)
            state_receiver_thread.daemon = True     # 데몬 쓰레드로 지정
            state_receiver_thread.start()    # 병렬처리 시작

            threads_initialized = True		# 드론과의 통신하기 위한 초기 설정이 완료된 상태

        # drones = {'드론 IP 주소' : { 'responses': [], 'state': {} } }
        drones[host] = {
            'responses': [],
            'state': {},
        }

    def get_own_udp_object(self):
        global drones

        host = self.address[0]  # 드론 IP 주소
        return drones[host]     # { 'responses': [], 'state': {} } 형태로 반환하기

    @staticmethod   # 정적 메소드
    def udp_response_receiver():
        """내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음. 드론의 응답을 받는 함수. 백그라운드 스레드에서 실행해야 함."""
        while True:		# 항상 실행됨
            try:
                data, address = client_socket.recvfrom(1024)    # client_socket 소켓으로부터 메시지를 읽고 클라이언트(드론)의 주소도 같이 가져옴
                # 반환값 : (데이터, (드론 IP주소, Port번호))

                address = address[0]    # 드론 IP 주소
                Tello.LOGGER.debug('Data received from {} at client_socket'.format(address))

                if address not in drones:      # 드론 IP 주소가 drones(dict)에 없다면
                    continue

                # drones = {'드론 IP 주소' : { 'responses': [data1], 'state': {data2} } } 에서
                # responses의 list에 요소 추가하기
                drones[address]['responses'].append(data)

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod   # 정적 메소드
    def udp_state_receiver():
        """백그라운드 스레드에서 실행해야 함. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음. 드론의 상태정보를 받는 함수"""
        state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # state_socket 소켓 생성
        state_socket.bind(('', Tello.STATE_UDP_PORT))   # 서버의 IP와 Port 고정하기

        while True:     # 항상 실행됨
            try:
                data, address = state_socket.recvfrom(1024)   # state_socket 소켓으로부터 메시지를 읽고 클라이언트(드론)의 주소도 같이 가져옴
                # 반환값 : (데이터, (드론 IP주소, Port번호))

                address = address[0]    # 드론 IP 주소
                Tello.LOGGER.debug('Data received from {} at state_socket'.format(address))

                if address not in drones:       # 드론 IP 주소가 drones(dict)에 없다면
                    continue

                data = data.decode('ASCII')
                # drones = {'드론 IP 주소' : { 'responses': [data1], 'state': {data2} } }
                # state에 data내용 추가하기
                drones[address]['state'] = Tello.parse_state(data)

            except Exception as e:
                Tello.LOGGER.error(e)
                break

    @staticmethod   # 정적 메소드
    def parse_state(state: str) -> dict:
        """내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음. str로 온 상태 메시지 분석하는 정적함수. str을 dict로 변경"""
        state = state.strip()   # 양쪽에서 공백을 제거
        Tello.LOGGER.debug('Raw state data: {}'.format(state))

        if state == 'ok':
            return {}

        state_dict = {}     # 센서값을 저장할 빈 dict 생성
        for field in state.split(';'):  # 문자열 중 ;를 기준으로 나누기
            split = field.split(':')    # 문자열 중 :를 기준으로 나누기
            if len(split) < 2:
                continue

            key = split[0]      # 센서의 변수명
            value = split[1]    # 센서의 값

            if key in Tello.state_field_converters:     # key가 Tello 드론의 내장 센서 변수명 중에 있다면
                try:
                    value = Tello.state_field_converters[key](value)    # 해당 변수명이 key와 같은 곳에 value를 할당하기
                except Exception as e:
                    Tello.LOGGER.debug('Error parsing state value for {}: {} to {}'
                                       .format(key, value, Tello.state_field_converters[key]))
                    Tello.LOGGER.error(e)

            state_dict[key] = value

        return state_dict

    def get_current_state(self) -> dict:
        """드론의 상태를 확인하는 함수. 모든 필드가 포함된 dict를 반환. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음"""
        return self.get_own_udp_object()['state']   # { 'responses': [data1], 'state': {data2} }에서 {data2}란 dict만 반환

    def get_state_field(self, key: str):
        """이름으로 특정 상태 필드 가져오기. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음"""
        state = self.get_current_state()

        if key in state:
            return state[key]
        else:
            raise Exception('Could not get state property ' + key)

    def get_mission_pad_id(self) -> int:
        return self.get_state_field('mid')

    def get_mission_pad_distance_x(self) -> int:
        return self.get_state_field('x')

    def get_mission_pad_distance_y(self) -> int:
        return self.get_state_field('y')

    def get_mission_pad_distance_z(self) -> int:
        return self.get_state_field('z')

    def get_pitch(self) -> int:
        return self.get_state_field('pitch')

    def get_roll(self) -> int:
        return self.get_state_field('roll')

    def get_yaw(self) -> int:
        return self.get_state_field('yaw')

    def get_speed_x(self) -> int:
        return self.get_state_field('vgx')

    def get_speed_y(self) -> int:
        return self.get_state_field('vgy')

    def get_speed_z(self) -> int:
        return self.get_state_field('vgz')

    def get_acceleration_x(self) -> float:
        return self.get_state_field('agx')

    def get_acceleration_y(self) -> float:
        return self.get_state_field('agy')

    def get_acceleration_z(self) -> float:
        return self.get_state_field('agz')

    def get_lowest_temperature(self) -> int:
        return self.get_state_field('templ')

    def get_highest_temperature(self) -> int:
        return self.get_state_field('temph')

    def get_temperature(self) -> float:
        templ = self.get_lowest_temperature()
        temph = self.get_highest_temperature()
        return (templ + temph) / 2

    def get_height(self) -> int:
        return self.get_state_field('h')

    def get_distance_tof(self) -> int:
        return self.get_state_field('tof')

    def get_barometer(self) -> int:
        return self.get_state_field('baro') * 100

    def get_flight_time(self) -> int:
        return self.get_state_field('time')

    def get_battery(self) -> int:
        return self.get_state_field('bat')

    def get_udp_video_address(self) -> str:
        """내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음"""
        return 'udp://@' + self.VS_UDP_IP + ':' + str(self.VS_UDP_PORT)  # + '?overrun_nonfatal=1&fifo_size=5000'
        # udp://@0.0.0.0:11111 란 문자열(스트리밍 url) 반환

    def get_video_capture(self):
        """드론에서 VideoCapture 개체를 가져옴. 사용자가 get_frame_read를 대신 사용하기를 원함.
        Returns: VideoCapture """

        if self.cap is None:    # cap이 None 이라면
            self.cap = cv2.VideoCapture(self.get_udp_video_address())   # 스트리밍 url 에서 영상을 가져와 cap 변수에 VideoCapture 객체를 담음

        if not self.cap.isOpened():  # 영상이 정상적으로 열리지 않았다면(초기화되지 않았다면)
            self.cap.open(self.get_udp_video_address())     # 영상파일을 열기

        return self.cap     # VideoCapture 객체 반환

    def get_frame_read(self) -> 'BackgroundFrameRead':
        """드론에서 BackgroundFrameRead 객체를 가져옴. 그런 다음, backgroundFrameRead.frame을 호출하여 드론에 의해 실제 프레임을 수신.
        Returns: BackgroundFrameRead """
        
        if self.background_frame_read is None:   # background_frame_read이 None이라면(background_frame_read을 None으로 초기화해 놓음)
            self.background_frame_read = BackgroundFrameRead(self, self.get_udp_video_address())    # BackgroundFrameRead 객체를 생성
            self.background_frame_read.start()  # BackgroundFrameRead 에서 정의한 start()함수로 self.worker 란 쓰레드를 실행
        return self.background_frame_read   # BackgroundFrameRead 객체를 반환

    def stop_video_capture(self):
        return self.streamoff()

    # command는 문자열, timeout은 RESPONSE_TIMEOUT(7)이란 정수란 type을 가짐
    def send_command_with_return(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> str:
        """드론에게 명령을 전송하고 응답을 기다림. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음.
        Return: bool/str . str(성공에 대한 응답 텍스트 포함), False(성공하지 않을 경우 False)"""

        diff = time.time() - self.last_received_command_timestamp   # diff = 현재 시각 - 가장 최근에 command를 보낸 시간
        if diff < self.TIME_BTW_COMMANDS:   # 명령어사이의 최소의 대기 시간보다 diff가 작다면
            self.LOGGER.debug('Waiting {} seconds to execute command {}...'.format(diff, command))
            time.sleep(diff)    # diff 만큼 대기

        self.LOGGER.info('Send command: ' + command)
        timestamp = time.time()     # 현재 시각 반환(명령어를 드론에게 보낸 시간)

        # client_socket 소켓으로 데이터 전송(명령어 보내기)
        # sendto(전달할 데이터, 데이터를 전달할 주소=드론의 IP와 Port)
        client_socket.sendto(command.encode('utf-8'), self.address)

        responses = self.get_own_udp_object()['responses']  # { 'responses': [data1], 'state': {data2} }에서 [data1]란 list만 변수에 할당
        while len(responses) == 0:  # 리스트에 아무것도 없다면
            if time.time() - timestamp > timeout:   # (현재 시각 - 명령어를 드론에게 보낸 시간)이 timeout(최대 응답 대기 시간)보다 크다면
                self.LOGGER.warning('Timeout exceed on command ' + command)
                return "Timeout error!"
            else:
                time.sleep(0.1)

        self.last_received_command_timestamp = time.time()      # 현재 시각 반환

        # udp_response_receiver 함수로 인해 항상 응답이 responses의 list에 추가됨
        response = responses.pop(0)     # responses란 list의 맨 앞의 요소를 response로 반환 (맨 앞의 요소는 삭제)
        response = response.decode('utf-8').rstrip("\r\n")  # 문자열의 오른쪽 공백 지우기

        self.LOGGER.info('Response {}: {}'.format(command, response))

        return response

    def send_command_without_return(self, command: str):
        """응답을 기다리지 않고 드론에게 명령 전송. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음"""
        # Commands very consecutive makes the drone not respond to them. So wait at least self.TIME_BTW_COMMANDS seconds

        self.LOGGER.info('Send command (no expect response): ' + command)
        client_socket.sendto(command.encode('utf-8'), self.address)     # client_socket 소켓으로 데이터 전송(명령어 보내기)

    def send_control_command(self, command: str, timeout: int = RESPONSE_TIMEOUT) -> bool:
        """드론에게 명령어를 전달하고 응답을 기다림. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음."""
        response = "max retries exceeded"
        for i in range(0, self.retry_count):    # 재시도 횟수만큼 반복함
            response = self.send_command_with_return(command, timeout=timeout)      # 명령어 문자열과 timeout을 전달하기

            if response == 'OK' or response == 'ok':
                return True     # 응답이 OK면 True 반환

            # 응답이 OK가 아니면
            self.LOGGER.debug('Command attempt {} for {} failed'.format(i, command))

        self.raise_result_error(command, response)  # 예외를 발생시킴
        return False  # never reached

    def send_read_command(self, command: str) -> str:
        """드론에게 지정된 명령을 전송하고 응답을 기다림. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음"""

        response = self.send_command_with_return(command)

        try:
            response = str(response)    # 명령어 결과를 문자열로 하여 변수에 저장
        except TypeError as e:  # TypeError가 발생하면
            self.LOGGER.error(e)
            pass

        # 명령어 결과에 error, ERROR, False 가 없다면
        if ('error' not in response) and ('ERROR' not in response) and ('False' not in response):
            return response
            if response.isdigit():  # 명령어 결과인 문자열이 숫자라면
                return int(response)    # 명령어 결과를 int로 변환하여 반환
            else:   # 명령어 결과인 문자열이 숫자가 아니라면
                try:
                    # isdigit()는 숫자가 실수(float)일 때 false을 반환하므로
                    return float(response)  # 명령어 결과를 float로 변환하여 반환
                except ValueError:  # ValueError가 발생하면 : 연산이나 함수가 올바른 형이지만 부적절한 값을 가진 인자를 받음
                    return response     # 문자열 그대로 반환
        else:   # 명령어 결과에 error, ERROR, False가 있다면
            self.raise_result_error(command, response)
            return "error: this code should never be reached"

    def send_read_command_int(self, command: str) -> int:
        """드론에게 지정된 명령을 전송하고 응답을 기다림. 응답을 정수로 인식하여 분석하기. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음"""
        response = self.send_read_command(command)
        return int(response)

    def send_read_command_float(self, command: str) -> float:
        """드론에게 지정된 명령을 전송하고 응답을 기다림. 응답을 실수로 인식하여 분석하기. 내부적인 함수, 일반적으로 사용자가 직접 호출하지 않음"""
        response = self.send_read_command(command)
        return float(response)

    def raise_result_error(self, command: str, response: str) -> bool:
        raise Exception('Command {} was unsuccessful. Message: {}'.format(command, response))   # 예외를 발생시킴

    def connect(self, wait_for_state=True):
        self.send_control_command("command")

        if wait_for_state:  # 항상 조건이 True
            for i in range(20):  # 20번 동안 반복하기
                if self.get_current_state():
                    Tello.LOGGER.debug('connect() received first state packet after {} seconds'.format(i * 0.05))
                    break

                time.sleep(0.05)

            if not self.get_current_state():
                raise Exception('Did not receive a state packet from the Tello')

    def takeoff(self):
        self.send_control_command("takeoff", timeout=20)
        self.is_flying = True   # 드론이 날고 있는지 여부(날고 있음)

    def land(self):
        self.send_control_command("land")
        self.is_flying = False  # 드론이 날고 있는지 여부(날고 있지 않음)

    def streamon(self):
        """비디오 스트리밍 켜기. 이후에는 tello.get_frame_read 를 사용. AP 모드일 때 드론에서 지원됨.
        Currently Tello EDUs do not support video streaming while connected to a wifi network."""
        self.send_control_command("streamon")
        self.stream_on = True   # 스트리밍 여부(재생 중)

    def streamoff(self):
        self.send_control_command("streamoff")
        self.stream_on = False  # 스트리밍 여부(스트리밍 정지)

    def emergency(self):
        self.send_control_command("emergency")

    def move(self, direction: str, x: int):
        self.send_control_command(direction + ' ' + str(x))

    def move_up(self, x: int):
        self.move("up", x)

    def move_down(self, x: int):
        self.move("down", x)

    def move_left(self, x: int):
        self.move("left", x)

    def move_right(self, x: int):
        self.move("right", x)

    def move_forward(self, x: int):
        self.move("forward", x)

    def move_back(self, x: int):
        self.move("back", x)

    def rotate_clockwise(self, x: int):
        self.send_control_command("cw " + str(x))

    def rotate_counter_clockwise(self, x: int):
        self.send_control_command("ccw " + str(x))

    def flip(self, direction: str):
        self.send_control_command("flip " + direction)

    def flip_left(self):
        self.flip("l")

    def flip_right(self):
        self.flip("r")

    def flip_forward(self):
        self.flip("f")

    def flip_back(self):
        self.flip("b")

    def go_xyz_speed(self, x: int, y: int, z: int, speed: int):
        self.send_control_command('go %s %s %s %s' % (x, y, z, speed))

    def curve_xyz_speed(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int):
        self.send_control_command('curve %s %s %s %s %s %s %s' % (x1, y1, z1, x2, y2, z2, speed))

    def go_xyz_speed_mid(self, x: int, y: int, z: int, speed: int, mid: int):
        self.send_control_command('go %s %s %s %s m%s' % (x, y, z, speed, mid))

    def curve_xyz_speed_mid(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, speed: int, mid: int):
        self.send_control_command('curve %s %s %s %s %s %s %s m%s' % (x1, y1, z1, x2, y2, z2, speed, mid))

    def go_xyz_speed_yaw_mid(self, x: int, y: int, z: int, speed: int, yaw: int, mid1: int, mid2: int):
        self.send_control_command('jump %s %s %s %s %s m%s m%s' % (x, y, z, speed, yaw, mid1, mid2))

    def enable_mission_pads(self):
        self.send_control_command("mon")

    def disable_mission_pads(self):
        self.send_control_command("moff")

    def set_mission_pad_detection_direction(self, x):
        self.send_control_command("mdirection " + str(x))

    def set_speed(self, x: int):
        self.send_control_command("speed " + str(x))

    def send_rc_control(self, left_right_velocity: int, forward_backward_velocity: int, up_down_velocity: int,
                        yaw_velocity: int):
        def round_to_100(x: int):
            if x > 100:
                return 100
            if x < -100:
                return -100
            return x

        if time.time() - self.last_rc_control_timestamp > self.TIME_BTW_RC_CONTROL_COMMANDS:
            self.last_rc_control_timestamp = time.time()
            self.send_command_without_return('rc %s %s %s %s' % (round_to_100(left_right_velocity),
                                                                round_to_100(forward_backward_velocity),
                                                                round_to_100(up_down_velocity),
                                                                round_to_100(yaw_velocity)))

    def set_wifi_credentials(self, ssid, password):
        self.send_command_without_return('wifi %s %s' % (ssid, password))

    def connect_to_wifi(self, ssid, password):
        self.send_command_without_return('ap %s %s' % (ssid, password))

    def query_speed(self) -> int:
        return self.send_read_command_int('speed?')

    def query_battery(self) -> int:
        return self.send_read_command_int('battery?')

    def query_flight_time(self) -> int:
        return self.send_read_command_int('time?')

    def query_height(self) -> int:
        return self.send_read_command_int('height?')

    def query_temperature(self) -> int:
        return self.send_read_command_int('temp?')

    def query_attitude(self) -> dict:
        response = self.send_read_command('attitude?')
        return Tello.parse_state(response)

    def query_barometer(self) -> int:
        return self.send_read_command_int('baro?') * 100

    def query_distance_tof(self) -> float:
        # example response: 801mm
        return int(self.send_read_command('tof?')[:-2]) / 10

    def query_wifi_signal_noise_ratio(self) -> str:
        return self.send_read_command('wifi?')

    def query_sdk_version(self) -> str:
        return self.send_read_command('sdk?')

    def query_serial_number(self) -> str:
        return self.send_read_command('sn?')

    def end(self):
        """드론의 tello 객체를 종료하려면 이 메서드를 호출"""
        if self.is_flying:  # 날고 있다면
            self.land()

        if self.stream_on:  # 스트리밍 중이라면
            self.streamoff()

        if self.background_frame_read is not None:  # BackgroundFrameRead 객체가 None이 아니라면(쓰레드가 실행 중이라면)
            self.background_frame_read.stop()

        if self.cap is not None:    # VideoCapture 객체가 있다면(None이 아니라면)
            self.cap.release()      # 리소스 반환

        host = self.address[0]  # 드론 IP 주소
        if host in drones:  # drones 란 dict에 '드론 IP 주소'가 있다면
            del drones[host]    # dict 요소 삭제하기. drones 란 dict 객체를 삭제함
            # drones = {'드론 IP 주소' : { 'responses': [], 'state': {} } }

    def __del__(self):
        self.end()


class BackgroundFrameRead:
    """비디오 캡처의 프레임을 백그라운드에서 읽음. backgroundFrameRead.frame을 사용하여 현재 프레임을 가져옴"""

    def __init__(self, tello, address):
        tello.cap = cv2.VideoCapture(address)   # VideoCapture 객체를 생성하여 tello.cap 변수에 담기
        self.cap = tello.cap

        if not self.cap.isOpened():     # 영상이 정상적으로 열리지 않았다면(초기화되지 않았다면)
            self.cap.open(address)      # 영상 열기

        self.grabbed, self.frame = self.cap.read()  # 한 프레임씩 읽음. 프레임 읽은 결과 grabbed(True/False)와 frame(읽은 프레임) 반환
        if not self.grabbed or self.frame is None:      # 프레임을 읽기가 실패이거나 프레임이 None이라면
            raise Exception('Failed to grab first frame from video stream')

        self.stopped = False    # 프레임 재생하기 (False : 재생 중)
        self.worker = Thread(target=self.update_frame, args=(), daemon=True)    # Thread 객체 생성, update_frame 함수를 백그라운드에서 실행 예정

    def start(self):
        self.worker.start()     # 쓰레드 시작(update_frame 함수를 병렬 처리 시작)

    def update_frame(self):
        while not self.stopped:     # 프레임이 재생 중(False)일 동안에는
            if not self.grabbed or not self.cap.isOpened():     # 프레임을 읽기가 실패이거나 영상이 정상적으로 열리지 않았다면(초기화되지 않았다면)
                self.stop()     # stop 함수 호출
            else:   # 프레임을 정상적으로 읽었거나, 정상적으로 열렸다면
                (self.grabbed, self.frame) = self.cap.read()    # 한 프레임씩 읽기

    def stop(self):
        self.stopped = True     # 프레임 정지하기 (True : 정지)
        self.worker.join()      # 해당 쓰레드에서 실행되는 함수(update_frame)가 종료될때까지 기다림
