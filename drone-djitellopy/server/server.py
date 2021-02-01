import config
from flask import render_template, request, jsonify, Response

app = config.app    # Flask 인스턴스 가져오기

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mode/')
def mode():
    return render_template('mode.html')

@app.route('/mode/controller/')
def controller():
    return render_template('controller.html')

@app.route('/monitor/')
def monitor():
    return render_template('monitor.html')

def run():
    # flask 서버 실행하기
    # threaded 사용하도록 설정(동시 request를 처리 가능)
    app.run(host=config.WEB_ADDRESS, port=config.WEB_PORT, threaded=True)


# __name__ : 모듈의 이름이 저장되는 변수
if __name__ == '__main__':    # 해당 파이썬 파일이 프로그램의 시작점이 맞는지 판단하는 작업
    run()