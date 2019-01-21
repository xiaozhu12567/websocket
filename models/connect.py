from sqlalchemy import create_engine

HOSTNAME = '127.0.0.1'
PORT = '3306'
DATABASE = 'websocket'
USERNAME = 'root'
PASSWORD = '123.coM'

db_url = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8'.format(
    USERNAME, PASSWORD, HOSTNAME, PORT, DATABASE
)

engine = create_engine(db_url)

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base(engine)         # 是创建所有模型类的基类

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(engine)          # 用于执行所有sql语句
session = Session()

if __name__ == '__main__':
    connection = engine.connect()
    result = connection.execute('select 1')
    print(result.fetchone())