# droneapp/controllers/server.py
# flask 실행하기 위한 파일

import logging
import config
from flask import render_template, request, jsonify, Response
# jsonify : 사용자가 json data를 내보내도록 제공

from droneapp.models.drone_manager import DroneManager
import droneapp.models.course

logger = logging.getLogger(__name__)    # getLogger의 인자로는 만들고 싶은 로거 이름을 전달
app = config.app    # Flask 인스턴스 가져오기

def get_drone():
    return DroneManager()   # DroneManager를 global 선언한 것 처럼 사용

@app.route('/')
def index():
    return render_template('index.html')

# 컨트롤러 화면 라우팅
@app.route('/controller/')
def controller():
    return render_template('controller.html')

# Flask의 이미지 버튼으로 명령어 전달
@app.route('/api/command/', methods=['POST'])
def command():
    cmd = request.form.get('command')
    logger.info({'action': 'command', 'cmd': cmd})
    drone = get_drone()
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
        drone.up()
    if cmd =='down':
        drone.down()
    if cmd == 'forward':
        drone.forward()
    if cmd == 'back':
        drone.back()
    if cmd == 'clockwise':
        drone.clockwise()
    if cmd == 'counterClockwise':
        drone.counter_clockwise()
    if cmd == 'left':
        drone.left()
    if cmd == 'right':
        drone.right()
    if cmd == ' flipFront':
        drone.flip_front()
    if cmd == 'flipBack':
        drone.flip_back()
    if cmd == 'flipLeft':
        drone.flip_left()
    if cmd == 'flipRight':
        drone.flip_right()
    if cmd == 'patrol':
        drone.patrol()
    if cmd == 'stopPatrol':
        drone.stop_patrol()
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

def video_generator():
    drone = get_drone()
    for jpeg in drone.video_jpeg_generator():
        yield (b'--frame\r\n'
               b'COntent-Type: image/jpeg\r\n\r\n' +
               jpeg + b'\r\n\r\n')

@app.route('/video/streaming')
def video_feed():
    return Response(video_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 코스를 불러오기
def get_courses(course_id=None):
    drone = get_drone()
    courses = droneapp.models.course.get_courses(drone)
    if course_id:
        return courses.get(course_id)
    return courses

@app.route('/games/shake/')
def game_shake():
    courses = get_courses()
    return render_template('games/shake.html', courses=courses)

@app.route('/api/shake/start', methods=['GET', 'POST'])
def shake_start():
    course_id = request.args.get('id')      # GET 방식일 경우
    # course_id = request.form.get('id')    # POST 방식일 경우
    course = get_courses(int(course_id))
    course.start()
    return jsonify(result='started'), 200

@app.route('/api/shake/run', methods=['GET', 'POST'])
def shake_run():
    course_id = request.args.get('id')
    # course_id = request.form.get('id')
    course = get_courses(int(course_id))
    course.run()
    return jsonify(
        elapsed=course.elapsed,
        status=course.status,
        running=course.is_running), 200

def run():
    # flask 서버 실행하기
    # threaded 사용하도록 설정(동시 request를 처리 가능)
    app.run(host=config.WEB_ADDRESS, port=config.WEB_PORT, threaded=True)