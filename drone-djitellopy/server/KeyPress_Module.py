import pygame

def init():
    pygame.init()
    win = pygame.display.set_mode((400, 400))  # 화면 사이즈 (w, h)

def main():
    def getKey(keyName):
        ans = False

        # 모든 이벤트 또는 이벤트 유형 (유형을 인수로 전달하여)을 큐에서 가져옴
        for eve in pygame.event.get():
            pass

        # 어느 키가 눌렸는지 변수에 할당
        keyInput = pygame.key.get_pressed()  # 모든 키의 상태 목록을 반환

        # 문자열이 객체의 속성중 하나의 이름이면, 결과는 그 속성값
        myKey = getattr(pygame, 'K_{}'.format(keyName))

        print('K_{}'.format(keyName))

        if keyInput[myKey]:
            ans = True

        pygame.display.update()

        return ans


if __name__ == '__main__':
    init()
    while True:  # 무한루프
        main()