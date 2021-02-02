import config
from flask import render_template, request, jsonify, Response
from djitellopy import tello

app = config.app    # Flask 인스턴스 가져오기

DEFAULT_DISTANCE = 30  # 기본 드론 움직이는 거리
DEFAULT_SPEED = 10  # 기본 드론 스피드 설정
DEFAULT_DEGREE = 15    # 기본 각도

def get_drone():
    return tello.Tello()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mode/')
def mode():
    return render_template('mode.html')

@app.route('/mode/controller/')
def controller():
    return render_template('controller.html')

# Flask의 이미지 버튼으로 명령어 전달
@app.route('/web/command/', methods=['POST'])
def command():
    cmd = request.form.get('command')
    drone = get_drone()
    if cmd == 'takeOff':
        drone.takeoff()
    if cmd == 'land':
        drone.land()
    if cmd == 'speed':
        speed = request.form.get('speed')
        if speed:
            drone.set_speed(int(speed))
    if cmd == 'up':
        drone.move_up(DEFAULT_DISTANCE)
    if cmd == 'down':
        drone.move_down(DEFAULT_DISTANCE)
    if cmd == 'forward':
        drone.move_forward(DEFAULT_DISTANCE)
    if cmd == 'back':
        drone.move_back(DEFAULT_DISTANCE)
    if cmd == 'clockwise':
        drone.rotate_clockwise(DEFAULT_DISTANCE)
    if cmd == 'counterClockwise':
        drone.rotate_counter_clockwise(DEFAULT_DISTANCE)
    if cmd == 'left':
        drone.move_left(DEFAULT_DISTANCE)
    if cmd == 'right':
        drone.move_right(DEFAULT_DISTANCE)
    if cmd == ' flipFront':
        drone.flip_forward(DEFAULT_DISTANCE)
    if cmd == 'flipBack':
        drone.flip_back(DEFAULT_DISTANCE)
    if cmd == 'flipLeft':
        drone.flip_left(DEFAULT_DISTANCE)
    if cmd == 'flipRight':
        drone.flip_right(DEFAULT_DISTANCE)

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