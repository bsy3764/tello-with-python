# main.py

import sys
import logging
import droneapp.controllers.server
import config

logging.basicConfig(level=logging.INFO,      # 로깅 레벨을 설정
                    stream=sys.stdout)     # 터미널에 출력
                    #filename=config.LOG_FILE)   # 로깅 내용을 해당 파일에 저장

# __name__ : 모듈의 이름이 저장되는 변수
if __name__=='__main__':    # 해당 파이썬 파일이 프로그램의 시작점이 맞는지 판단하는 작업
    droneapp.controllers.server.run()