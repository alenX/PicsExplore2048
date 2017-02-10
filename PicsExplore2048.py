# -*- coding: utf-8 -*-
import base64
import os
import pymongo
import random
import redis
import re
import datetime
import flask_login

from PIL import Image
from flask import Flask, render_template, jsonify, request, json, make_response, url_for, redirect, send_from_directory
from bson.objectid import ObjectId
from flask_login import LoginManager, login_required, login_user, logout_user, user_logged_in
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, current_user, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flaskext.markdown import Markdown

from ext import db as mysql_db
from models import User
from uploader import Uploader
from decorator import login_and_admin
from views.mib_view import mib_v
from views.blog_view import blog_v

app = Flask(__name__)
Markdown(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config.from_object('config')
mysql_db.init_app(app)
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "/blog/login"
login_manager.init_app(app)
jinja_env = app.jinja_env

client = pymongo.MongoClient("localhost", 27017)
db = client['find_2048']
blogs = client['blogs']
info = db["bs64_info"]
reds = redis.Redis(host='localhost', port=6379, db=0)
reds.flushdb()
all_count = info.count()
reds.set('num', random.randint(1, all_count))
is_load = False
EVERY_NUM = 3  # 每页数量
with app.app_context():
    mysql_db.create_all()


@app.route('/')
def hello_world():
    return redirect(url_for('explore_pic'))


@app.route('/test')
def test():
    return render_template('test.html')


@app.route('/explore')
def explore_pic():
    pic_path = os.path.join(app.root_path + '/static/cache/image/')
    for root, dirs, files in os.walk(pic_path):
        reds.set(files, files)
    return render_template('pics.html', pic_url='../static/image/225_133828_b3e21.jpg')


@app.route('/explore/next', methods=['POST'])
def explore_pic_next():
    print(reds.get('num'))
    reds.set('num', int(reds.get('num')) + 1)
    pics = down_image()
    return jsonify(pics)


@app.route('/explore/pre', methods=['POST'])
def explore_pic_pre():
    print(reds.get('num'))
    reds.set('num', int(reds.get('num')) - 1)
    pics = down_image()
    return jsonify(pics)


def down_image():
    for i in info.find().limit(1).skip(int(int(reds.get('num')) % all_count) + 1):
        title = i['title']
        if reds.exists(title) == 0:  # 避免重复下载
            with open(os.path.join(app.root_path + '/static/cache/image/', title), "wb") as t:
                t.write(base64.b64decode(i['bs64']))
                t.flush()
            reds.set(str(title), str(title) + '')
        p = Image.open(os.path.join(app.root_path + '/static/cache/image/', title))
        return {'title': '../static/cache/image/' + title, 'height': p.size[0], 'width': p.size[1]}


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/upload/', methods=['GET', 'POST', 'OPTIONS'])
def upload():
    """UEditor文件上传接口

    config 配置文件
    result 返回结果
    """
    mimetype = 'application/json'
    result = {}
    action = request.args.get('action')

    # 解析JSON格式的配置文件
    with open(os.path.join(app.static_folder, 'ue', 'jsp',
                           'config.json')) as fp:
        try:
            # 删除 `/**/` 之间的注释
            CONFIG = json.loads(re.sub(r'\/\*.*\*\/', '', fp.read()))
        except:
            CONFIG = {}

    if action == 'config':
        # 初始化时，返回配置文件给客户端
        result = CONFIG

    elif action in ('uploadimage', 'uploadfile', 'uploadvideo'):
        # 图片、文件、视频上传
        if action == 'uploadimage':
            fieldName = CONFIG.get('imageFieldName')
            config = {
                "pathFormat": CONFIG['imagePathFormat'],
                "maxSize": CONFIG['imageMaxSize'],
                "allowFiles": CONFIG['imageAllowFiles']
            }
        elif action == 'uploadvideo':
            fieldName = CONFIG.get('videoFieldName')
            config = {
                "pathFormat": CONFIG['videoPathFormat'],
                "maxSize": CONFIG['videoMaxSize'],
                "allowFiles": CONFIG['videoAllowFiles']
            }
        else:
            fieldName = CONFIG.get('fileFieldName')
            config = {
                "pathFormat": CONFIG['filePathFormat'],
                "maxSize": CONFIG['fileMaxSize'],
                "allowFiles": CONFIG['fileAllowFiles']
            }

        if fieldName in request.files:
            field = request.files[fieldName]
            uploader = Uploader(field, config, app.static_folder)
            result = uploader.getFileInfo()
        else:
            result['state'] = '上传接口出错'

    elif action in ('uploadscrawl'):
        # 涂鸦上传
        fieldName = CONFIG.get('scrawlFieldName')
        config = {
            "pathFormat": CONFIG.get('scrawlPathFormat'),
            "maxSize": CONFIG.get('scrawlMaxSize'),
            "allowFiles": CONFIG.get('scrawlAllowFiles'),
            "oriName": "scrawl.png"
        }
        if fieldName in request.form:
            field = request.form[fieldName]
            uploader = Uploader(field, config, app.static_folder, 'base64')
            result = uploader.getFileInfo()
        else:
            result['state'] = '上传接口出错'

    elif action in ('catchimage'):
        config = {
            "pathFormat": CONFIG['catcherPathFormat'],
            "maxSize": CONFIG['catcherMaxSize'],
            "allowFiles": CONFIG['catcherAllowFiles'],
            "oriName": "remote.png"
        }
        fieldName = CONFIG['catcherFieldName']

        if fieldName in request.form:
            # 这里比较奇怪，远程抓图提交的表单名称不是这个
            source = []
        elif '%s[]' % fieldName in request.form:
            # 而是这个
            source = request.form.getlist('%s[]' % fieldName)

        _list = []
        for imgurl in source:
            uploader = Uploader(imgurl, config, app.static_folder, 'remote')
            info = uploader.getFileInfo()
            _list.append({
                'state': info['state'],
                'url': info['url'],
                'original': info['original'],
                'source': imgurl,
            })

        result['state'] = 'SUCCESS' if len(_list) > 0 else 'ERROR'
        result['list'] = _list

    else:
        result['state'] = '请求地址出错'

    result = json.dumps(result)

    if 'callback' in request.args:
        callback = request.args.get('callback')
        if re.match(r'^[\w_]+$', callback):
            result = '%s(%s)' % (callback, result)
            mimetype = 'application/javascript'
        else:
            result = json.dumps({'state': 'callback参数不合法'})

    res = make_response(result)
    res.mimetype = mimetype
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Headers'] = 'X-Requested-With,X_Requested_With'
    return res


# @app.route('/mib/index')
# def mib_index():
#     return render_template('tools/mib_info.html')
#
#
# @app.route('/mib/upload', methods=['POST', 'GET'])
# def mib_upload():
#     if request.method == 'POST':
#         files = request.files.getlist("file")
#         for f in filter(lambda d: str(d.filename).endswith('.mib'), files):
#             mib_file_name = f.filename
#             f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(mib_file_name)))
#             with open(os.path.join(app.config['UPLOAD_FOLDER'], mib_file_name), "r") as p:
#                 line = ''
#                 for mib in p.readlines():
#                     s = mib[:-1]
#                     if 'OBJECT-TYPE' in s:
#                         if 'DESCRIPTION' in line.strip() and line.strip().startswith('zx'):
#                             mib_line = line.strip()
#                             mib_name = mib_line.split()[0]
#                             mib_desc = mib_line.split('DESCRIPTION')[1].strip().split('"')[1]
#                             mib_info.insert(
#                                 {'mib_name': mib_name, 'mib_desc': mib_desc, 'time': datetime.datetime.now()})
#                         line = ''
#                     line += s
#             os.remove(os.path.join(app.config['UPLOAD_FOLDER'], mib_file_name))
#     return redirect(url_for('mib_index'))
#
#
# @app.route('/mib/query', methods=['GET', 'POST'])
# def mib_query():
#     mib_name = request.form['mib_name']
#     mib = mib_info.find_one({'mib_name': str(mib_name).strip()})
#     if mib:
#         return jsonify({'desc': mib['mib_desc']})
#     return jsonify({'desc': '不存在该记录'})


def i_sub_str(i_str, s, e):
    return i_str[s:e]


def i_normal_markdown(i_str):
    return i_str.replace("\n", "\\n")


if __name__ == '__main__':
    jinja_env.filters['i_sub_str'] = i_sub_str
    jinja_env.filters['i_normal_markdown'] = i_normal_markdown
    app.register_blueprint(mib_v)
    app.register_blueprint(blog_v)
    app.run()
