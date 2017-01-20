# -*- coding: utf-8 -*-
from flask_login import UserMixin
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from PicsExplore2048 import mysql_db as db

Base = declarative_base()


class User(UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, index=True)
    password = Column(String(64))

    def __init__(self, name, password):
        self.name = name
        self.password = password

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def is_active(self):
        return True

    def get_id(self):
        return self.id
