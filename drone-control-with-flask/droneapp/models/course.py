# droneapp/models/course.py

import logging
import time
from droneapp.models.base import Singleton

logger = logging.getLogger(__name__)

class BaseCourse(metaclass=Singleton):
    def __init__(self, name, drone):
        self.name = name
        self.status = 0     # 드론의 상태
        self.is_running = False     # 드론이 코스를 진행 중인지 확인
        self.start_time = None      # 드론이 코스를 시작한 시간
        self.elapsed = None     # 드론이 코스를 진행한 시간
        self.drone = drone

    # 드론이 코스 진행을 시작하는 시간
    def start(self):
        self.start_time = time.time()
        self.is_running = True

    # 드론이 코스를 진행하는 것을 멈춤
    def stop(self):
        if not self.is_running:
            return False
        self.is_running = False
        self.status = 0

    def update_elapsed(self):
        if not self.is_running:
            return None
        self.elapsed = time.time() - self.start_time
        return self.elapsed

    # 코스에서 사용할 움직임의 순서들(패트톨) 정의
    # 오버라이드 할 예정
    def _run(self):
        raise NotImplementedError

    def run(self):
        if not self.is_running:
            return False
        self.status += 1
        self._run()
        self.update_elapsed()

class CourseA(BaseCourse):
    def _run(self):
        if self.status == 1:
            self.drone.takeoff()

        if self.status == 10 or self.status == 15 or self.status == 20 or self.status == 25:
            self.drone.clockwise(90)

        if self.status == 30:
            self.drone.flip_front()

        if self.status == 40:
            self.drone.flip_back()

        if self.status == 50:
            self.drone.land()
            self.stop()

class CourseB(BaseCourse):
    def _run(self):
        if self.status == 1:
            self.drone.takeoff()

        if self.status == 10:
            self.drone.flip_front()

        if self.status == 20:
            self.drone.flip_back()
            if self.elapsed and 10 < self.elapsed < 15:
                self.status = 45

        if self.status == 25:
            self.drone.flip_right()

        if self.status == 35:
            self.drone.flip_left()

        if self.status == 50:
            self.drone.land()
            self.stop()

# 코스를 만들어 반환
def get_courses(drone):
    return {
        1: CourseA('Course A', drone),
        2: CourseB('Course B', drone),
    }