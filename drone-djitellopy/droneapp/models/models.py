from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

# sqlalchemy로 테이블 생성하기
class Replay_list(db.Model):
	__tablename__ = 'replay_list'
	id = db.Column(db.Integer, primary_key=True)  # replay 순서
	replay_name = db.Column(db.String(100))  # replay 이름
	replay_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # replay가 생성 및 저장된 시간, 정렬을 위해


# 2초? 마다 명령어를 저장하기
class Sensor(db.Model):
	__tablename__ = 'Sensor'
	id = db.Column(db.Integer, primary_key=True)
	replay_id = db.Column(db.Integer, db.ForeignKey('replay_list.id'), unique=True)  # replay_list테이블의 replay의 id와 연결하기
	cmd = db.Column(db.String(100))  # 드론 명령어
	start_h = db.Column(db.Integer)  # replay의 시작 높이(cm단위)