from DJITelloPy.djitellopy import Tello
import threading
import time
import KeyPress_Module as kp
import cv2
import numpy as np
import math
import os

# 이미지 저장 장소
image_dir = os.path.isdir('C:\Test\drone\server\images')

######## MAPPING PARAMETERS ###########
fSpeed = 30  # Forward Speed in cm/s
aSpeed = 30  # Angular Speed Degrees/s
interval = 0.25     # 드론과 서버 통신의 딜레이(지연)

dInterval = fSpeed * interval
aInterval = aSpeed * interval

map_wight = 500     # map의 가로길이
map_height = 500    # map의 세로길이

map_x = int(map_wight / 2)  # map의 가운데 x좌표
map_y = int(map_height / 2) # map의 가운데 y좌표

a = 0
yaw = 0
points = [(0,0), (0,0)]
########################################

tello = Tello()

tello.connect()     # 드론에 연결하기

conneted = tello.send_command_with_return(command="command")

print("connect result :" + conneted)

# 드론 센서값
def drone_status():
    status_log = tello.get_current_state()
    print("stauts : {}".format(status_log))

status_log_thread = threading.Thread(target=drone_status)
status_log_thread.daemon = True  # 데몬 쓰레드로 지정
status_log_thread.start()  # 병렬처리 시작

# 긴급 정지
def stop():
    e_stop = input("stop() is doing~!!")
    if e_stop == "1":
        print("emergency all stop")
        tello.emergency()

emergency_thread = threading.Thread(target=stop)
emergency_thread.daemon = True  # 데몬 쓰레드로 지정
emergency_thread.start()  # 병렬처리 시작

# 키보드로 조작하는 함수
def getKeyboardInput():
    lr, fb, ud, yv = 0, 0, 0, 0
    speed = fSpeed
    aspeed = aSpeed
    d = 0
    global x, y, yaw, a, image_dir

    if kp.getKey("LEFT"):   # left
        lr = -speed     # API로 드론을 실제 이동시킴
        d = dInterval
        a = -180

    elif kp.getKey("RIGHT"):    # right
        lr = speed
        d = -dInterval
        a = -180

    if kp.getKey("UP"):     # forward
        fb = speed
        d = dInterval
        a = 270

    elif kp.getKey("DOWN"):     # back
        fb = -speed
        d = -dInterval
        a = -90

    if kp.getKey("w"):  # up
        ud = speed

    elif kp.getKey("s"):    # down
        ud = -speed

    if kp.getKey("a"):  # clockwise
        yv = -aspeed
        yaw -= aInterval

    elif kp.getKey("d"):    # counter_clockwise
        yv = aspeed
        yaw += aInterval

    if kp.getKey("q"):  # land
        tello.land()
        time.sleep(3)

    if kp.getKey("e"):  # takeoff
        tello.takeoff()

    if kp.getKey('z'):  # snapshot
        cv2.imwrite(image_dir + f'/{time.time()}.jpg', img)
        time.sleep(0.3)

    time.sleep(interval)
    a += yaw  #
    x += int(d * math.cos(math.radians(a)))
    y += int(d * math.sin(math.radians(a)))
    return [lr, fb, ud, yv, x, y]

# 지도 및 좌표 그리기
def mapping(img, points):
    for point in points:
        cv2.circle(img, point, 5, (0, 0, 255), cv2.FILLED)  # 빨간 드론의 이동 경로 기록
    cv2.circle(img, points[-1], 6, (0, 255,0), cv2.FILLED)  # 드론의 위치를 녹색으로 map에 표시
    cv2.putText(img, f'({(points[-1][0]-500)/ 100},{(points[-1][1]-500) / 100})m',
                (points[-1][0] + 10, points[-1][1] + 30), cv2.FONT_HERSHEY_PLAIN, 1,
                (255, 0, 255), 1)

# connect의 결과가 ok면 아래 진행
if conneted == 'ok':
    print("connected!!!!")

    # 배터리 상태 확인하기
    battery = tello.get_battery()
    print("battery: {}".format(battery))

    # 배터리가 30% 초과일 경우에만 실행
    if int(battery) > 30:
        print("battery is Good")

        # 드론 화면 보이기
        global img

        tello.streamon()
        img = tello.get_frame_read().frame
        img = cv2.resize(img, (360, 240))
        cv2.imshow('tello view', img)
        cv2.waitKey(1)

        mode = input("which mode do you want?")
        if mode == "keyboard":  # 키보드로 조작하기
            kp.init()

            while True:
                vals = getKeyboardInput()
                tello.send_rc_control(vals[0], vals[1], vals[2], vals[3])
                img = np.zeros((map_wight, map_height, 3), np.uint8)    # 검정 도화지 만들기
                if (points[-1][0] != vals[4] or points[-1][1] != vals[5]):
                    points.append((vals[4], vals[5]))

                mapping(img, points)
                cv2.imshow("drone Map", img)
                cv2.waitKey(1)

        if mode == "Remote":
            pass

    else:   # 배터리가 30% 이하일 경우에
        print("battery needs to be charged")

else:   # connect의 결과가 ok가 아니면
    print("Not conneted with Tello")