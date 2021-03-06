# droneapp/controllers/server.py
# flask 실행하기 위한 파일

import logging
import config
import cv2
from DJITelloPy.djitellopy.tello import Tello
from flask import render_template, request, jsonify, Response
import time
import datetime
# jsonify : 사용자가 json data를 내보내도록 제공

from droneapp.models.manual_control_pygame import FrontEnd
from droneapp.db_conn import Database

logger = logging.getLogger(__name__)    # getLogger의 인자로는 만들고 싶은 로거 이름을 전달
app = config.app    # Flask 인스턴스 가져오기

mode = 0    # 0: not save, 1: save
log = []    # 명령어를 저장하는 리스트
bef_cmd = 0  # replay 처음 시작인지 여부 확인
gap = []    # 명령어 사이간의 시간 차이

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

@app.route('/mode/detact/')
def detact():
    return render_template('detact.html')

# Flask의 이미지 버튼으로 명령어 전달
@app.route('/web/command/', methods=['POST'])
def command():
    cmd = request.form.get('command')  # POST로 전달받은 값
    logger.info({'action': 'command', 'cmd': cmd})
    drone = Tello()

    global mode
    if mode == 0:   # not save
        if cmd == 'command':
            drone.connect()
        if cmd == 'streamon':
            drone.streamon()
        if cmd == 'streamoff':
            drone.streamoff()
        if cmd == 'takeoff':
            drone.takeoff()
        if cmd == 'land':
            drone.land()
        if cmd == 'speed':
            speed = request.form.get('speed')
            logger.info({'action': 'command', 'cmd': cmd, 'speed': speed})
            if speed:
                drone.set_speed(int(speed))
        if cmd == 'up':
            speed = request.form.get('speed')
            drone.move_up(int(speed))
        if cmd == 'down':
            speed = request.form.get('speed')
            drone.move_down(int(speed))
        if cmd == 'forward':
            speed = request.form.get('speed')
            drone.move_forward(int(speed))
        if cmd == 'back':
            speed = request.form.get('speed')
            drone.move_back(int(speed))
        if cmd == 'clockwise':
            angle = request.form.get('angle')
            drone.rotate_clockwise(int(angle))
        if cmd == 'counterClockwise':
            angle = request.form.get('angle')
            drone.rotate_counter_clockwise(int(angle))
        if cmd == 'left':
            speed = request.form.get('speed')
            drone.move_left(int(speed))
        if cmd == 'right':
            speed = request.form.get('speed')
            drone.move_right(int(speed))
        if cmd == 'flipFront':
            drone.flip_front()
        if cmd == 'flipBack':
            drone.flip_back()
        if cmd == 'flipLeft':
            drone.flip_left()
        if cmd == 'flipRight':
            drone.flip_right()
        if cmd == 'faceDetectAndTrack':
            print("detect start")
        if cmd == 'stopFaceDetectAndTrack':
            print("detect stop")
        if cmd == 'snapshot':
            if drone.snapshot():
                return jsonify(status='success'), 200
            else:
                return jsonify(status='fail'), 400

    if mode == 1:   # save
        global log, replay_start, gap, bef_cmd, aft_cmd
        print("replay_start 2 :", replay_start)
        if not bef_cmd:  # bef_cmd 가 0이라면(replay 저장 시작 중 가장 먼저 눌린 버튼의 시간 체크하기 위해)
            log.append("start")
            bef_cmd = replay_start  # 이전 명령어 실행시간
            now_cmd = time.time()
            first_gap = now_cmd - replay_start
            print("first_cmd gap :", first_gap)
            print("first_cmd gap round :", round(first_gap, 1))
            log.append("wait," + str(round(first_gap, 1)))
        else:
            bef_cmd = aft_cmd
            now_cmd = time.time()
            cmd_gap = now_cmd - bef_cmd
            print("cmd gat time :", cmd_gap)
            print("cmd gap round :", round(cmd_gap, 1))
            log.append("wait," + str(round(cmd_gap, 1)))
        aft_cmd = time.time()   # 현재 명령어 실행시간
        cmd_gap = aft_cmd - bef_cmd # 명령어 사이의 시간 차
        print("log in :", log)
        if cmd == 'command':
            log.append('command')
            # print("log :", log)
            drone.connect()

        if cmd == 'streamon':
            log.append('streamon')
            # print("log :", log)
            drone.streamon()

        if cmd == 'streamoff':
            log.append('streamoff')
            # print("log :", log)
            drone.streamoff()

        if cmd == 'takeoff':
            log.append('takeoff')
            # print("log :", log)
            drone.takeoff()

        if cmd == 'land':
            log.append('land')
            # print("log :", log)
            drone.land()

        if cmd == 'speed':
            speed = request.form.get('speed')
            logger.info({'action': 'command', 'cmd': cmd, 'speed': speed})
            if speed:
                log.append('speed {}'.format(speed))
                # print("log :", log)
                drone.set_speed(int(speed))

        if cmd == 'up':
            speed = request.form.get('speed')
            log.append('up {}'.format(speed))
            # print("log :", log)
            drone.move_up(int(speed))

        if cmd == 'down':
            speed = request.form.get('speed')
            log.append('down {}'.format(speed))
            # print("log :", log)
            drone.move_down(int(speed))

        if cmd == 'forward':
            speed = request.form.get('speed')
            log.append('forward {}'.format(speed))
            # print("log :", log)
            drone.move_forward(int(speed))

        if cmd == 'back':
            speed = request.form.get('speed')
            log.append('back {}'.format(speed))
            # print("log :", log)
            drone.move_back(int(speed))

        if cmd == 'clockwise':
            angle = request.form.get('angle')
            log.append('cw {}'.format(angle))
            # print("log :", log)
            drone.rotate_clockwise(int(angle))

        if cmd == 'counterClockwise':
            angle = request.form.get('angle')
            log.append('ccw {}'.format(angle))
            # print("log :", log)
            drone.rotate_counter_clockwise(int(angle))

        if cmd == 'left':
            speed = request.form.get('speed')
            log.append('left {}'.format(speed))
            # print("log :", log)
            drone.move_left(int(speed))

        if cmd == 'right':
            speed = request.form.get('speed')
            log.append('right {}'.format(speed))
            # print("log :", log)
            drone.move_right(int(speed))

        if cmd == 'flipFront':
            log.append('flip f')
            # print("log :", log)
            drone.flip_front()

        if cmd == 'flipBack':
            log.append('flip b')
            # print("log :", log)
            drone.flip_back()

        if cmd == 'flipLeft':
            log.append('flip l')
            # print("log :", log)
            drone.flip_left()

        if cmd == 'flipRight':
            log.append('flip r')
            # print("log :", log)
            drone.flip_right()

        if cmd == 'faceDetectAndTrack':
            print("detect start")
        if cmd == 'stopFaceDetectAndTrack':
            print("detect stop")
        if cmd == 'snapshot':
            if drone.snapshot():
                return jsonify(status='success'), 200
            else:
                return jsonify(status='fail'), 400

    print("log out :", log)
    return jsonify(status='success'), 200

@app.route('/key/command/')
def keyboard_cmd():
    drone = FrontEnd()
    drone.run()
    return render_template('Keyboard.html')

@app.route('/replay/create/', methods=['POST'])
def create_replay():    # replay record start
    global repl_id
    print("create replay start")
    global replay_start
    replay_start = time.time()  # replay 시작하는 시간, 기준이 되는 시간
    print("replay_start 1 :", replay_start)
    replay_name = request.form.get('replay')
    print("replay_name : {}".format(replay_name))
    replay_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("replay_date : {}".format(replay_date))

    # DB 연결할 객체
    db_class = Database()

    # replay_list 테이블 삽입
    sql = "insert into replay_list(replay_name) values ({})".format(replay_name)
    db_class.execute(sql)
    db_class.commit()

    #  replay_list 에서 가장 큰 id값 1개만 가져오기
    sql1 = "select max(id) from replay_list"
    repl_id = db_class.executeOne(sql1)
    repl_id = repl_id['max(id)']
    print("create replay id : {}".format(repl_id))  # create replay id : {'max(id)': 3}

    global mode
    mode = 1    # save

    return render_template('controller.html')

@app.route('/replay/save/', methods=['POST'])
def save_replay():    # DB에 저장하기
    global log, repl_id, aft_cmd
    replay_end = time.time()  # replay 종료하는 시간
    finish_cmd = replay_end - aft_cmd
    print("last cmd ~ save gap :", finish_cmd)
    print("last cmd ~ save gap round :", round(finish_cmd, 1))
    log.append("wait," + str(round(finish_cmd, 1)))
    log.append("end")
    replay_name = request.form.get('replay')
    print("save replay id : {}".format(repl_id))
    print("final log :", log)

    # DB 연결할 객체
    db_class = Database()

    # Sensor 테이블 삽입
    # log list를 for문으로 하여 내용이 없을 때까지 insert하게 만들기
    for cmd in log:
        print("cmd : {}".format(cmd))
        sql = "insert into Sensor(replay_id, cmd) values (%s, %s)"
        row = db_class.execute(sql, (repl_id, cmd))

    db_class.commit()

    global mode
    mode = 0    # not save

    return render_template('controller.html')

def get_replay_list():
    # DB 연결할 객체
    db_class = Database()

    # replay 목록을 가져오는 sql
    sql2 = "select * from replay_list order by id asc"

    row = db_class.executeAll(sql2)
    print("get replay_list :", row)

    return row

@app.route('/replay/list/')
def replay_list():
    get_replay = get_replay_list()
    return render_template('replay_list.html', data_list=get_replay)

@app.route('/replay/play/', methods=['POST'])
def replay_play():
    replay_id = request.form.get('replay_id')  # POST로 전달받은 값
    print("replay_id :", replay_id)

    # DB 연결할 객체
    db_class = Database()

    # replay 목록을 가져오는 sql
    sql1 = "select replay_name from replay_list where id={}".format(replay_id)
    row = db_class.executeAll(sql1)
    print("sql1 result 1 :", row)     # [{'replay_name': '55'}]
    print("sql1 result 2 :", row[0]['replay_name'])

    cmd_list = []
    sql2 = "select * from Sensor where replay_id={}".format(replay_id)
    row = db_class.executeAll(sql2)
    print("sql2 result 1 :", row)
    for cmd_read in row:    # db에 저장된 명령어를 리스트에 추가시킴
        print("cmd 1 :", cmd_read)
        cmd = cmd_read['cmd']
        print("cmd 2 :", cmd)
        cmd_list.append(cmd)
        print("cmd_list :", cmd_list)

    drone = Tello()

    # replay 내용을 drone에게 전달
    for cmd in cmd_list:
        print("cmd 3 :", cmd)
        if cmd == 'start':
            continue
        elif cmd == 'end':
            break
        elif 'wait' in cmd:
            print("wait time :", cmd)
            _, wait_time = cmd.split(',')
            print("time :", wait_time)
            time.sleep(float(wait_time))
        else:
            print("drone cmd :", cmd)
            result = drone.send_command_with_return(cmd)
            if result == 'ok' or result == 'OK':
                continue
            else:
                print("{} command fail!!!!!!".format(cmd))

    return render_template('replay_list.html')

# Generator(제네레이터) : iterator(값을 차례대로 꺼낼 수 있는 객체)를 생성해주는 함수
# def video_generator():
def gen_frames():
    drone = Tello()
    for jpeg in drone.video_jpeg_generator():
        # yield으로 순차 출력
        # M JPEG : 영상을 표현하기 위해 JPEG 이미지(.jpg 와 같은 확장자를 사용)를 시간순에 따라 나열한 방식
        # Content-Type (반송 파일 형식으로) multipart / x-mixed-replace(multipart/x-mixed-replace (MIME 형식))를 이용
        yield (b'--frame\r\n'   # 프레임
               b'Content-Type: image/jpeg\r\n\r\n' +    # 데이터 형식
               jpeg + b'\r\n\r\n')  # jpeg 이미지 데이터

@app.route('/video/streaming')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/monitor/')
def monitor():
    return render_template('monitor.html')

def run():
    # flask 서버 실행하기
    # threaded 사용하도록 설정(동시 request를 처리 가능)
    app.run(host=config.WEB_ADDRESS, port=config.WEB_PORT, threaded=True)