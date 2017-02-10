# -*- coding: utf-8 -*-
from flask import Flask
app = Flask(__name__)
DEBUG = True
# SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://root:1128@localhost:3306/blog?charset=utf8'
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/user.db'
SQLALCHEMY_COMMIT_ON_TEARDOWN = True
SQLALCHEMY_TRACK_MODIFICATIONS = True
SECRET_KEY='hard to guess AAA'
UPLOAD_FOLDER=app.root_path+'/static/cache'
HEADER_PIC_FOLDER=app.root_path+'/static/image'
