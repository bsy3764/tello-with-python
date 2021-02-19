# config.py

import os
from flask import Flask

WEB_ADDRESS = '0.0.0.0'
WEB_PORT = 5000

# __file__ : 현재 수행중인 코드를 담고 있는 파일의 위치
# os.path.abspath(파일명) : 해당 파일의 절대 경로 확인
# os.path.dirname(경로+파일) : 파일에서 디렉토리 명만 알아냄
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 파일의 경로 지정하기
TEMPLATES = os.path.join(PROJECT_ROOT, 'droneapp/templates')
STATIC_FOLDER = os.path.join(PROJECT_ROOT, 'droneapp/static')

# 디버그 모드 설정
DEBUG = False

# 로그 파일
LOG_FILE = 'tello.log'

# Flask 인스턴스를 생성
app = Flask(__name__, template_folder=TEMPLATES, static_folder=STATIC_FOLDER)

if DEBUG:   # 만약 디버그 모드라면
    app.debug = DEBUG   # flask의 debug모드 활성화