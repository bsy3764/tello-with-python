# tools/single.py

# 싱글톤을 학습하기 위한 파일(실제 프로젝트엔 필요 없음)
# 싱글톤 패턴
# 인스턴스를 하나만 생성하여 사용하기 위한 디자인 패턴
# 실행중인 프로세스에서 오로지 하나의 인스턴스만을 유지하기 위해 생성자에 접근 제한을 두고,
# 유일한 단일 객체를 반환하기 위해 정적 메소드를 사용
# 유일한 단일객체 역시 정적 참조변수가 필요

class Singleton(type):
    _instance = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instance:    # 처음 불려졌다면
            print('call')
            cls._instance[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance[cls]

# T란 클래스가 싱글톤이 됨
class T(metaclass=Singleton):
#class T(object):   # 싱글톤과 기본 클래스의 결과 비교
    def __init__(self):
        print('init')

test = T()
test = T()
test = T()
test = T()
test = T()

