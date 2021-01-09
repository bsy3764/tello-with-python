import logging
import socket
import sys
import time
import threading

logging.basicConfig(level = logging.INFO, stream = sys.stdout)
logger = logging.getLogger(__name__)

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
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM))
		
		# 소켓에 주소, 포트 할당
		self.socket.bind((self.host_ip, self.host_port))
	
		# 드론의 상태 메시지
		self.response = None    # 변수 None으로 초기화
		self.stop_event = threading.Event()    # 상태 메시지 그만 받기
		
		# target에 메서드(함수)의 이름 전달
		# args에는 튜플이 들어감
		self._response_thread = threading.Thread(target=self.receive_response, 
									args=(self.stop_event, ))
		self._response_thread.start()    # 쓰레드 시작(병렬 처리 시작)
		
		# 데이터 보내기(드론에게 명령어 전달)
		self.send_command('command')
		self.send_command('streamon')
		
	def receive_response(self, stop_event):
		while not stop_event.is_set():    # stop_event가 이벤트가 오기 전까지 반복
			try:
				self.response, ip = self.socket.recvfrom(3000)    # 버퍼 사이즈를 3000
				logger.info({'action' : 'receive_response', 'response' : self.response})
			except socket.error as ex:
				logger.error({'action' : 'receive_response', 'ex' : ex})
				break
					
	def __dell__(self):
		self.stop()    # stop함수 호출
	
	def stop(self):
		self.stop_event.set()    # 이벤트를 설정
		
		# 쓰레드에서 메시지를 보내려는데, 이미 close한 소켓으로 인하여 에러 메시지 발생
		# 메시지를 다 받을 때 까지는 잠시 대기하게 만들기
		retry = 0
		while self._response_thread.isAlive():    # 쓰레드가 살아 있다면
			time.sleep(0.3)    # 0.3초 대기
			if retry > 30:   # 0.3초씩 대기를 30번 넘게 한다면
				break
			retry += 1
		
		self.socket.close()    # 소켓 연결을 닫고 연결된 리소스를 모두 해제

	def send_command(self, command):    # 명령어 전달 하는 함수
		logger.info({'action' : 'send_command', 'command' : command})    # 전달하는 명령어를 로그로 남기기
		self.socket.sendto(command.encode('utf-8'), self.drone_address)

		# 메시지를 다 받을 때 까지는 잠시 대기하게 만들기
		retry = 0
		while self.response is None:
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
		return self.send_command('takeoff')    # takeoff란 문자열을 send_command함수에 전달
		
	def land(self):
		return self.send_command('land')

# __name__ : 모듈의 이름이 저장되는 변수
if __name__ == '__main__':    # 해당 파이선 파일이 프로그램의 시작점이 맞는지 판단하는 작업
	drone_manager = DroneManager()
	drone_manager.takeoff()
	
	time.sleep(10)    # 10초간 대기
	
	drone_manager.land()
	drone_manager.stop()