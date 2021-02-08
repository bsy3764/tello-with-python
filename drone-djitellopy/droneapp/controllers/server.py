# droneapp/controllers/server.py
# flask 실행하기 위한 파일

import logging
import config
from DJITelloPy.djitellopy import tello
from flask import render_template, request, jsonify, Response
# jsonify : 사용자가 json data를 내보내도록 제공

from droneapp.models.drone_manager import DroneManager
from droneapp.models.manual_control_pygame import FrontEnd
import droneapp.models.course

logger = logging.getLogger(__name__)    # getLogger의 인자로는 만들고 싶은 로거 이름을 전달
app = config.app    # Flask 인스턴스 가져오기

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mode/')
def mode():
    return render_template('mode.html')

# 컨트롤러 화면 라우팅
@app.route('/mode/controller/')
def controller():
    return render_template('controller.html')

# Flask의 이미지 버튼으로 명령어 전달
@app.route('/web/command/', methods=['POST'])
def command():
    cmd = request.form.get('command')   # POST로 전달받은 값
    logger.info({'action': 'command', 'cmd': cmd})
    drone = tello.Tello()
    # default_speed = drone.set_speed(30)
    if cmd == 'command':
        drone.connect()
    if cmd == 'streamon':
        drone.streamon()
    if cmd == 'takeOff':
        drone.takeoff()
    if cmd == 'land':
        drone.land()
    if cmd == 'speed':
        speed = request.form.get('speed')
        logger.info({'action': 'command', 'cmd': cmd, 'speed': speed})
        if speed:
            drone.set_speed(int(speed))
    if cmd == 'up':
        drone.move_up()
    if cmd == 'down':
        drone.move_down()
    if cmd == 'forward':
        drone.move_forward()
    if cmd == 'back':
        drone.move_back()
    if cmd == 'clockwise':
        drone.rotate_clockwise()
    if cmd == 'counterClockwise':
        drone.rotate_counter_clockwise()
    if cmd == 'left':
        drone.move_left()
    if cmd == 'right':
        drone.move_right()
    if cmd == ' flipFront':
        drone.flip_front()
    if cmd == 'flipBack':
        drone.flip_back()
    if cmd == 'flipLeft':
        drone.flip_left()
    if cmd == 'flipRight':
        drone.flip_right()
    if cmd == 'faceDetectAndTrack':
        drone.enable_face_detect()
    if cmd == 'stopFaceDetectAndTrack':
        drone.disable_Face_detect()
    if cmd == 'snapshot':
        if drone.snapshot():
            return jsonify(status='success'), 200
        else:
            return jsonify(status='fail'), 400

    return jsonify(status='success'), 200

@app.route('/key/command/')
def keyboard_cmd():
    drone = FrontEnd()
    drone.run()

@app.route('/replay/create/')
def create_replay():
    print("create replay start")

def video_generator():
    drone = tello.Tello()
    for jpeg in drone.video_jpeg_generator():
        yield (b'--frame\r\n'
               b'COntent-Type: image/jpeg\r\n\r\n' +
               jpeg + b'\r\n\r\n')

@app.route('/video/streaming')
def video_feed():
    return Response(video_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 코스를 불러오기
def get_courses(course_id=None):
    drone = tello.Tello()
    courses = droneapp.models.course.get_courses(drone)
    if course_id:
        return courses.get(course_id)
    return courses

@app.route('/monitor/')
def monitor():
    return render_template('monitor.html')

def run():
    # flask 서버 실행하기
    # threaded 사용하도록 설정(동시 request를 처리 가능)
    app.run(host=config.WEB_ADDRESS, port=config.WEB_PORT, threaded=True)