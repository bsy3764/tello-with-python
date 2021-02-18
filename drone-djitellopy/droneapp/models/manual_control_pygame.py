from djitellopy import Tello
import cv2
import pygame
import numpy as np
import time

S = 60  # 드론 스피드

# Pygame 창 디스플레이의 초당 프레임 수
# 입력 정보가 프레임당 한 번 처리되기 때문에 숫자가 적으면 입력 지연이 발생
FPS = 120

class FrontEnd(object):
    """ Tello 디스플레이를 유지하고 키보드 키를 통해 이동.
        Press escape key to quit.
        The controls are:
            - T: Takeoff
            - L: Land
            - 방향키: Forward, backward, left and right.
            - A: Counter clockwise
            - D: clockwise
            - W: up
            - S: down.
    """

    def __init__(self):
        # pygame 초기화
        pygame.init()

        # pygame window창 생성
        pygame.display.set_caption("Tello video stream")    # 타이틀바의 텍스트를 설정
        self.screen = pygame.display.set_mode([960, 720])   # 화면 해상도를 960*720 으로 초기화

        self.tello = Tello()

        # 드론 속도 -100 ~ 100
        self.for_back_velocity = 0
        self.left_right_velocity = 0
        self.up_down_velocity = 0
        self.yaw_velocity = 0
        self.speed = 10

        self.send_rc_control = False

        # 타이머를 업데이트
        pygame.time.set_timer(pygame.USEREVENT + 1, 1000 // FPS)

    def run(self):
        self.tello.connect()
        self.tello.set_speed(self.speed)

        # 스트리밍이 켜져 있는 경우, 이스케이프 키 없이 이 프로그램을 종료할 때 이런 일이 발생.
        self.tello.streamoff()
        self.tello.streamon()

        # 드론의 카메라 프레임 읽어오기
        frame_read = self.tello.get_frame_read()

        should_stop = False
        while not should_stop:  # should_stop가 False라면

            for event in pygame.event.get():
                if event.type == pygame.USEREVENT + 1:
                    self.update()
                elif event.type == pygame.QUIT:
                    should_stop = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        should_stop = True
                    else:
                        self.keydown(event.key)
                elif event.type == pygame.KEYUP:
                    self.keyup(event.key)

            if frame_read.stopped:
                break

            self.screen.fill([0, 0, 0])     # 화면을 지우기 위해 호출(검정색)

            frame = frame_read.frame
            text = "Battery: {}%".format(self.tello.get_battery())
            cv2.putText(frame, text, (5, 720 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.rot90(frame)
            frame = np.flipud(frame)

            frame = pygame.surfarray.make_surface(frame)
            self.screen.blit(frame, (0, 0))     # 지정한 좌표가 이미지의 왼쪽 위에 위치하도록 출력
            pygame.display.update()

            time.sleep(1 / FPS)

        # 종료할 때 항상 호출, 리소스 회수
        self.tello.end()

    def keydown(self, key):
        """ 키가 눌렸을 경우
        Arguments:
            key: pygame key
        """
        if key == pygame.K_UP:  # forward
            self.for_back_velocity = S
        elif key == pygame.K_DOWN:  # backward
            self.for_back_velocity = -S
        elif key == pygame.K_LEFT:  # left
            self.left_right_velocity = -S
        elif key == pygame.K_RIGHT:  # right
            self.left_right_velocity = S
        elif key == pygame.K_w:  # up
            self.up_down_velocity = S
        elif key == pygame.K_s:  # down
            self.up_down_velocity = -S
        elif key == pygame.K_a:  # counter clockwise
            self.yaw_velocity = -S
        elif key == pygame.K_d:  # clockwise
            self.yaw_velocity = S

    def keyup(self, key):
        """ 키를 안누른 상태
        Arguments:
            key: pygame key
        """
        if key == pygame.K_UP or key == pygame.K_DOWN:  # set zero forward/backward
            self.for_back_velocity = 0
        elif key == pygame.K_LEFT or key == pygame.K_RIGHT:  # set zero left/right
            self.left_right_velocity = 0
        elif key == pygame.K_w or key == pygame.K_s:  # set zero up/down
            self.up_down_velocity = 0
        elif key == pygame.K_a or key == pygame.K_d:  # set zero yaw
            self.yaw_velocity = 0
        elif key == pygame.K_t:  # takeoff
            self.tello.takeoff()
            self.send_rc_control = True
        elif key == pygame.K_l:  # land
            not self.tello.land()
            self.send_rc_control = False

    def update(self):
        """ 드론에게 전달할 명령어 업데이트 """
        if self.send_rc_control:
            self.tello.send_rc_control(self.left_right_velocity, self.for_back_velocity,
                                       self.up_down_velocity, self.yaw_velocity)


def main():
    frontend = FrontEnd()

    # run frontend
    frontend.run()


if __name__ == '__main__':
    main()
