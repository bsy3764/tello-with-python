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

global img

######## MAPPING PARAMETERS ###########
fSpeed = 10  # Forward Speed in cm/s (맵에서의 스피드)
aSpeed = 30  # Angular Speed Degrees/s (맵에서의 각도)
interval = 0.25  # 얼마간의 시간 간격으로 체크

dInterval = fSpeed * interval
aInterval = aSpeed * interval

map_wight = 500     # map의 가로길이
map_height = 500    # map의 세로길이

map_x_center = int(map_wight / 2)  # map의 가운데 x좌표
map_y_center = int(map_height / 2)  # map의 가운데 y좌표

map_x = int(map_wight / 2)  # 드론의 x좌표
map_y = int(map_height / 2)  # 드론의 y좌표

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

status_log_thread = threading.Thread(target=drone_status)   # 병렬처리할 함수를 지정하기
# status_log_thread.daemon = True  # 데몬 쓰레드로 지정
status_log_thread.start()  # 병렬처리 시작

# 긴급 정지
def stop():
    e_stop = input("stop() is doing~!!")
    if e_stop == "1":
        print("emergency all stop")
        tello.emergency()

# emergency_thread = threading.Thread(target=stop)    # 병렬처리할 함수를 지정하기
# emergency_thread.daemon = True  # 데몬 쓰레드로 지정
# emergency_thread.start()  # 병렬처리 시작

# 드론 화면 보이기
def droneview():
    tello.streamon()    # 드론의 프레임 시작하기
    while True:
        img = tello.get_frame_read().frame  # 드론의 프레임 읽어오기
        img = cv2.resize(img, (360, 240))   # 화면 사이즈 변경
        cv2.imshow('tello view', img)   # 화면으로 보여주기
        cv2.waitKey(1)

# 키보드로 조작하는 함수
def getKeyboardInput():
    lr, fb, ud, yv = 0, 0, 0, 0
    speed = 15  # 드론의 실제 이동할 스피드
    aspeed = aSpeed
    d = 0
    global map_x, map_y, yaw, a, image_dir

    if kp.getKey("LEFT"):   # left
        lr = -speed     # API로 드론을 실제 이동시킴
        d = dInterval   # 매핑의 좌표를 이동
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
        cv2.imwrite(image_dir + f'/{time.time()}.jpg', img)     # 이미지 저장하기
        time.sleep(0.3)

    # 내비 좌표 움직임 계산하기
    time.sleep(interval)
    a += yaw
    # print("be x : " + str(map_x))
    map_x += int(d * math.cos(math.radians(a)))     # 이동한 값 * 코사인값(각도 = 라디안)
    # print("af x : " + str(map_x))

    # print("be y : " + str(map_y))
    map_y += int(d * math.sin(math.radians(a)))     # 이동한 값 * 사인값(각도 = 라디안)
    # print("af y : " + str(map_y))
    return [lr, fb, ud, yv, map_x, map_y]

# 지도 및 좌표 그리기
def mapping(map, points):
    for point in points:
        cv2.circle(map, point, 5, (0, 0, 255), cv2.FILLED)  # 빨간 드론의 이동 경로 기록
    cv2.circle(map, points[-1], 6, (0, 255,0), cv2.FILLED)  # 드론의 위치를 녹색으로 map에 표시
    # print("lr : " + str(points[-1][0]))
    # print("fb : " + str(points[-1][1]))
    cv2.putText(map, f'({(points[-1][0] - map_x_center) / 100},{(points[-1][1] - map_y_center) / 100})m',  # 좌표 숫자
                (points[-1][0] + 10, points[-1][1] + 30), cv2.FONT_HERSHEY_PLAIN, 1,  # 좌표 표시 위치
                (0, 255, 255), 1)

# connect의 결과가 ok면 아래 진행
if conneted == 'ok':
    print("connected!!!!")

    # 배터리 상태 확인하기
    battery = tello.get_battery()
    print("battery: {}".format(battery))

    # 배터리가 30% 초과일 경우에만 실행
    if int(battery) > 30:
        print("battery is Good")

        while True:
            # 화면 보이기 선택
            video = input("video start?")
            if video == 'yes' or 'y':
                droneview_thread = threading.Thread(target=droneview)   # 병렬처리할 함수를 지정하기
                droneview_thread.start()  # 병렬처리 시작
            elif video == 'no' or 'n':
                if droneview_thread.is_alive():  # 이미 드론의 프레임을 받고 있던 상태라면
                    tello.streamoff()
                else:    # 드론의 프레임을 받지 않고 있던 상태라면
                    pass

            time.sleep(2)

            # 모드 선택하기
            mode = input("which mode do you want?")

            # 키보드 조작
            if mode in ['k', 'K']:  # 키보드로 조작하기
                kp.init()   # 키보드 입력을 받기위해

                emergency_thread = threading.Thread(target=stop)    # 병렬처리할 함수를 지정하기
                emergency_thread.daemon = True  # 데몬 쓰레드로 지정
                emergency_thread.start()  # 병렬처리 시작

                while True:
                    vals = getKeyboardInput()
                    tello.send_rc_control(vals[0], vals[1], vals[2], vals[3])   # 드론 움직이기
                    map = np.zeros((map_wight, map_height, 3), np.uint8)    # 검정 도화지 만들기
                    if (points[-1][0] != vals[4] or points[-1][1] != vals[5]):
                        points.append((vals[4], vals[5]))

                    mapping(map, points)
                    cv2.imshow("drone Map", map)    # 좌표 그리기
                    cv2.waitKey(1)

            # 웹으로 조작
            if mode in ['R', 'r']:
                print("Remote mode ~ !!!!!")

            if mode in ['0']:
                stopping = False
                break


    else:   # 배터리가 30% 이하일 경우에
        print("battery needs to be charged")

else:   # connect의 결과가 ok가 아니면
    print("Not conneted with Tello")