# -*- coding: utf-8 -*-
import base64
import os
import pymongo
import random
import redis
import re
import datetime

from PIL import Image
from flask import Flask, render_template, jsonify, request, json, make_response, url_for, redirect, g
from bson.objectid import ObjectId
from flask_login import LoginManager, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, current_user, AnonymousUserMixin

from uploader import Uploader

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://root:1128@localhost:3306/blog?charset=utf8'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True  # warning信息屏蔽
mysql_db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "/blog/login"
login_manager.init_app(app)
jinja_env = app.jinja_env

client = pymongo.MongoClient("localhost", 27017)
db = client['find_2048']
blogs = client['blogs']
info = db["bs64_info"]
blog = blogs['blog']
reds = redis.Redis(host='localhost', port=6379, db=0)
reds.flushdb()
all_count = info.count()
reds.set('num', random.randint(1, all_count))
is_load = False
EVERY_NUM = 6  # 每页数量


class User(UserMixin, mysql_db.Model):
    __tablename__ = 'users'
    id = mysql_db.Column(mysql_db.Integer, primary_key=True)
    username = mysql_db.Column(mysql_db.String(64), unique=True, index=True)
    password = mysql_db.Column(mysql_db.String(64))

    def __init__(self, id):
        self.id = id

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)


mysql_db.create_all()


@app.route('/')
def hello_world():
    return redirect(url_for('explore_pic'))


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


@app.route('/blog/list/<int:current>')
def blog_list(current=1):
    all_num = blog.count()
    if all_num % EVERY_NUM == 0:
        pages = all_num // EVERY_NUM
    else:
        pages = all_num // EVERY_NUM + 1
    all_blog = blog.find().limit(EVERY_NUM).skip((current - 1) * EVERY_NUM)
    return render_template('blog_list.html', blogs=all_blog, pages=pages, current=current)


@app.route('/blog/detail/<string:blog_id>')
def blog_detail(blog_id):
    current_blog = blog.find_one({'_id': ObjectId(blog_id)})  # bson
    if current_blog is None:
        return render_template('404.html'), 404
    return render_template('blog_detail.html', current_blog=current_blog)


@app.route('/blog/add')
@login_required
def blog_add():
    return render_template('blog_add.html')


@app.route('/blog/add_content/', methods=['POST'])
def add_content():
    paras = request.get_data()
    data = json.loads(paras)
    data['datetime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ids = blog.insert(data)
    return jsonify({'id': str(ids)})


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.route('/blog/login')
def blog_login():
    if current_user.get_id():
        return redirect(url_for('blog_list',current=1))
    return render_template('login.html')


@app.route('/blog/logout')
@login_required
def blog_logout():
    logout_user()
    return redirect(url_for('blog_list', current=1))


@app.route('/blog/login/reg', methods=['POST'])
def blog_login_reg():
    paras = request.get_data()
    user_para = json.loads(paras)
    user = User.query.filter_by(username=user_para['user'], password=base64.b64decode(user_para['password'])).first()
    if user:
        login_user(user)
        return jsonify({'rs': str('true')})
    else:
        return jsonify({'rs': str('false')})


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


def i_sub_str(i_str, s, e):
    return i_str[s:e]


if __name__ == '__main__':
    jinja_env.filters['i_sub_str'] = i_sub_str
    app.run()
