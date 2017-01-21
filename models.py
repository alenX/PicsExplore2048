# -*- coding: utf-8 -*-
from flask_login import UserMixin
from ext import db as mysql_db
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, mysql_db.Model):
    __tablename__ = 'users'
    id = mysql_db.Column(mysql_db.Integer, primary_key=True)
    username = mysql_db.Column(mysql_db.String(64), unique=True, index=True)
    password_hash = mysql_db.Column(mysql_db.String(256))

    # 不能读取
    @property
    def password(self):
        raise Exception("you cant read it")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password_hash(self, password):
        return check_password_hash(self.password_hash, password)

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)
