import logging
import socket
import sys
import time

logging.basicConfig(level=logging.INFO, stream=sys.stdout)  # 로깅 레벨을 설정
logger = logging.getLogger(__name__)    # getLogger의 인자로는 만들고 싶은 로거 이름을 전달


class DroneManager(object):
    def __init__(self, host_ip='192.168.10.2', host_port=8889,
                 drone_ip='192.168.10.1', drone_port=8889):
        self.host_ip = host_ip
        self.host_port = host_port
        self.drone_ip = drone_ip
        self.drone_port = drone_port
        self.drone_address = (drone_ip, drone_port)

        # 소켓 생성
        # UDP이므로 SOCK_DGRAM 사용
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 소켓에 주소, 포트 할당
        self.socket.bind((self.host_ip, self.host_port))    # 튜플 형태로 전달

        # 데이터 보내기(드론에게 명령어 전달)
        self.socket.sendto(b'command', self.drone_address)  # 드론을 맨 처음 실행 시, 입력해야 함
        self.socket.sendto(b'streamon', self.drone_address)  # 드론에서 영상을 스트리밍하기 시작

    # sendto(b'~~')에서 b를 사용하는 이유
    # Python에선 문자열이 유니코드이지만 네트워크에서 전송할 때는 바이트 여야하기 때문에
    # 리터럴(상수)의 경우 'b'for bytes 문자열을 추가

    # 클래스가 메모리에서 삭제되거나, 삭제하는 것을 잊으면
    def __dell__(self):
        self.stop()  # stop함수 호출

    def stop(self):
        self.socket.close()  # 소켓 연결을 닫고 연결된 리소스를 모두 해제

    def send_command(self, command):  # 명령어 전달 하는 함수
        logger.info({'action': 'send_command', 'command': command})  # 전달하는 명령어를 로그로 남기기
        self.socket.sendto(command.encode('utf-8'), self.drone_address) # 소켓에 명령어가 문자열로 오므로 인코딩 필요

    def takeoff(self):
        self.send_command('takeoff')  # takeoff란 문자열을 send_command함수에 전달

    def land(self):
        self.send_command('land')


# __name__ : 모듈의 이름이 저장되는 변수
if __name__ == '__main__':  # 해당 파이썬 파일이 프로그램의 시작점이 맞는지 판단하는 작업
    drone_manager = DroneManager()
    drone_manager.takeoff()

    time.sleep(5)  # 5초간 대기

    drone_manager.land()