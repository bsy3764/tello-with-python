import pymysql

class Database():
    def __init__(self):
        self.db = pymysql.connect(host='localhost',
                                  user='bit',
                                  password='123123',
                                  db='test',
                                  charset='utf8')
        self.cursor = self.db.cursor(pymysql.cursors.DictCursor)

    def execute(self, query, args={}):
        self.cursor.execute(query, args)
        print("query :{}".format(query))

    def executeOne(self, query, args={}):
        self.cursor.execute(query, args)
        row = self.cursor.fetchone()
        return row

    def executeAll(self, query, args={}):
        print("query :{}".format(query))
        self.cursor.execute(query, args)
        row = self.cursor.fetchall()
        return row

    def commit(self):
        self.db.commit()

# CREATE TABLE replay_list(
# 	id INT AUTO_INCREMENT PRIMARY KEY,
# 	replay_name VARCHAR(50),
# 	replay_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
# );
#
# CREATE TABLE Sensor(
# 	id INT AUTO_INCREMENT PRIMARY KEY,
# 	replay_id INT,
# 	cmd VARCHAR(50) null,
# 	start_h INT,
# 	FOREIGN KEY(replay_id) REFERENCES replay_list(id)
# );
