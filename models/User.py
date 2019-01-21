#coding=utf-8
from uuid import uuid4
from datetime import datetime
from string import printable        # 所有可打印的字符

from pbkdf2 import PBKDF2
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (create_engine, Column, Integer, String,
                        Text, Boolean, Date, DateTime, ForeignKey)

from .connect import Base
from .connect import session

class User(Base):
    __tablename__ = 'user'

    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False)
    _password = Column('password', String(64))
    createtime = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime)
    last_login = Column(DateTime)
    loginnum = Column(Integer, default=0)
    _locked = Column(Boolean, default=False, nullable=False)

    _avatar = Column(String(64))


    def _hash_password(self, password):
        return PBKDF2.crypt(password, iterations=0x2537)


    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = self._hash_password(password)

    def auth_password(self, other_password):
        if self._password:
            return self.password == PBKDF2.crypt(other_password, self.password)
        else:
            return False

    @property
    def avatar(self):
        return self._avatar if self._avatar else "default_avatar.jpeg"


    @avatar.setter
    def avatar(self, image_data):
        class ValidationError(Exception):                   # 自定义异常输出
            def __init__(self, message):
                super(ValidationError, self).__init__(message)
        if 64 < len(image_data) < 1024 * 1024:
            import imghdr
            import os
            ext = imghdr.what("", h=image_data)             # 获取文件拓展名
            print(ext)
            print(self.uuid)
 #           if ext in ['png', 'jpeg', 'gif', 'bmp'] and not self.is_xss_image(image_data):      # 如果拓展名在其中，并且不存在xss风险
            if ext in ['png', 'jpeg', 'gif', 'bmp']:      # 如果拓展名在其中，并且不存在xss风险
                if self._avatar and os.path.exists("static/images/useravatars/" + self._avatar):    # 检查记录是否存在，存在则删除
                    os.unlink("static/images/useravatars/" + self._avatar)      # 删除文件
                file_path = str("static/images/useravatars/" + self.uuid + '.' + ext)

                with open(file_path, 'wb') as f:
                    f.write(image_data)

                self._avatar = self.uuid + '.' + ext
            else:
                raise ValidationError("not in ['png', 'jpeg', 'gif', 'bmp']")
        else:
            raise ValidationError("64 < len(image_data) < 1024 * 1024 bytes")

#    def is_xss_image(self, data):
#        return all([char in printable for char in data[:16]])       # 由于图片是二进制存放，不是可打印字符，如果是可打印字符，可能存在xss攻击

    @classmethod
    def all(cls):
        return session.query(cls).all()

    @classmethod
    def by_id(cls, id):
        return session.query(cls).filter_by(id=id).first()

    @classmethod
    def by_uuid(cls, uuid):
        return session.query(cls).filter_by(uuid=uuid).first()

    @classmethod
    def by_name(cls, name):
        return session.query(cls).filter_by(username=name).first()

    @property
    def locked(self):
        return self._locked



    @locked.setter
    def locked(self, value):
        assert isinstance(value, bool)
        self._locked = value


    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'last_login': self.last_login,
        }

    def __repr__(self):
        return u'<User - id: %s  name: %s>' % (self.id,self.username)


if __name__ == '__main__':
    Base.metadata.create_all()