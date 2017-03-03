# -*- coding: utf-8 -*-
from flask_login import UserMixin
from ext import db as mysql_db
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, mysql_db.Model):
    __tablename__ = 'users'
    id = mysql_db.Column(mysql_db.Integer, primary_key=True)
    username = mysql_db.Column(mysql_db.String(64), unique=True, index=True)
    password = mysql_db.Column(mysql_db.String(256))
    login_count = mysql_db.Column(mysql_db.Integer, default=0)
    last_login_ip = mysql_db.Column(mysql_db.String(32), default='unknown')
    pic = mysql_db.Column(mysql_db.LargeBinary())
    nickname = mysql_db.Column(mysql_db.String(64))

    # 不能读取
    @property
    def pwd(self):
        raise Exception("you cant read it")

    @pwd.setter
    def pwd(self, password):
        self.password = generate_password_hash(password)

    def check_password_hash(self, password):
        return check_password_hash(self.password, password)

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)

    def is_admin(self):
        return self.username == 'admin'


class Comment(mysql_db.Model):
    __tablename__ = 'blog_comment'
    id = mysql_db.Column(mysql_db.Integer, primary_key=True)
    comment_id = mysql_db.Column(mysql_db.String(256))  # 评论的blog id
    comment_userid = mysql_db.Column(mysql_db.Integer)
    comment_username = mysql_db.Column(mysql_db.String(256))
    comment_time = mysql_db.Column(mysql_db.DateTime)
    comment = mysql_db.Column(mysql_db.String(256), default='Good 很棒')
