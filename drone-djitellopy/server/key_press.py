# mapping teset

import KeyPress_Module as kp
import numpy as np
from time import sleep
import cv2
import math

################ PARAMETERS ###################
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
###############################################

kp.init()

def getKeyboardInput():
    lr, fb, ud, yv = 0, 0, 0, 0
    # 오른쪽, 앞, 상승, 시계방향 : +
    # 왼쪽, 뒤, 하강, 반시계방향 : -
    speed = 15
    aspeed = 50
    global map_x, map_y, yaw, a
    d = 0

    if kp.getKey("LEFT"):
        lr = -speed
        d = dInterval
        a = -180

    elif kp.getKey("RIGHT"):
        lr = speed
        d = -dInterval
        a = 180

    if kp.getKey("UP"):
        fb = speed
        d = dInterval
        a = 270

    elif kp.getKey("DOWN"):
        fb = -speed
        d = -dInterval
        a = -90

    if kp.getKey("w"):
        ud = speed

    elif kp.getKey("s"):
        ud = -speed

    if kp.getKey("a"):
        yv = -aspeed
        yaw -= aInterval

    elif kp.getKey("d"):
        yv = aspeed
        yaw += aInterval

    # 실제 좌표를 계산하는 부분
    sleep(interval)
    a += yaw
    # print("be x : " + str(map_x))
    map_x += int(d * math.cos(math.radians(a)))
    # print("af x : " + str(map_x))
    
    # print("be y : " + str(map_y))
    map_y += int(d * math.sin(math.radians(a)))
    # print("af y : " + str(map_y))
    
    return [lr, fb, ud, yv, map_x, map_y]

def drawPoints(img, points):
    for point in points:
        cv2.circle(img, point, 5, (0, 0, 255), cv2.FILLED)
    cv2.circle(img, points[-1], 8, (0, 255,0), cv2.FILLED)
    
    # print("lr : " + str(points[-1][0]))
    # print("fb : " + str(points[-1][1]))
    # print("x : " + str((points[-1][0] - map_x_center)/100))
    # print("y : " + str((points[-1][1] - map_y_center)/100))
    
    cv2.putText(img, f'({(points[-1][0] - map_x_center)/100},{(points[-1][1] - map_y_center)/100})m', # 좌표 숫자
                (points[-1][0] + 10, points[-1][1] + 30), cv2.FONT_HERSHEY_PLAIN, 1,    # 좌표 표시 위치
                (0, 255, 255), 1)
                
    # print("==========================")

while True:
    vals = getKeyboardInput()
    img = np.zeros((map_wight, map_height, 3), np.uint8) # 검은색 도화지 생성
    if (points[-1][0] != vals[4] or points[-1][1] != vals[5]):
        points.append((vals[4], vals[5]))

    drawPoints(img, points)
    cv2.imshow("Output", img)
    cv2.waitKey(1)