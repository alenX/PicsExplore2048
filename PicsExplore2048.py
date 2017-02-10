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
blog = blogs['blog']
mib_info = blogs['mib_info']
user_mongo = blogs['user']
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
        return redirect(url_for('blog_list', current=1))
    return render_template('blog_detail.html', current_blog=current_blog)


@app.route('/blog/add')
@login_required
@login_and_admin
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
        return redirect(url_for('blog_list', current=1))
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
    user = User.query.filter_by(username=user_para['user']).first()
    if user and User.check_password_hash(user, user_para['password']):
        # if user:
        login_user(user)
        return jsonify({'rs': str('true')})
    else:
        return jsonify({'rs': str('false')})


@app.route('/blog/login/register', methods=['POST'])
def blog_login_register():
    paras = request.get_data()
    user_para = json.loads(paras)

    u = User()
    u.pwd = user_para['password']
    u.username = user_para['user']
    print(User.query.filter_by(username='admin').all())
    if u.username == 'admin' and User.query.filter_by(username='admin').first():
        return jsonify({'rs': str('false'), 'content': '不能使用admin用户注册'})
    mysql_db.session.add(u)
    mysql_db.session.commit()

    user = User.query.filter_by(username=u.username).first()

    if user:
        login_user(user)
        return jsonify({'rs': str('true')})
    else:
        return jsonify({'rs': str('false')})


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/blog/edit')
@login_required
def blog_edit():
    bs_pic = ''
    if user_mongo.find_one({'id': current_user.id}):
        img = user_mongo.find_one({'id': current_user.id})['pic_bs64']
        if img:
            if not os.path.isdir(os.path.join(app.config['HEADER_PIC_FOLDER'], str(current_user.id))):
                os.mkdir(os.path.join(app.config['HEADER_PIC_FOLDER'], str(current_user.id)))
            with open(os.path.join(app.config['HEADER_PIC_FOLDER'], str(current_user.id), 'header_img.jpg'), "wb") as p:
                p.write(base64.b64decode(img))
                p.flush()
            bs_pic = 'image/' + str(current_user.id) + '/' + 'header_img.jpg'
    return render_template('blog_edit.html', image=bs_pic, time=datetime.datetime.now().strftime('%Y%m%d%H%M%S'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/blog/upload', methods=['POST', 'GET'])
@login_required
def blog_upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
            # file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            with open(os.path.join(app.config['UPLOAD_FOLDER'], file.filename), "rb") as p:
                pic_bs64 = base64.b64encode(p.read())
                # user_mongo.delete_many({'id':current_user.id})
                if user_mongo.find_one({'id': current_user.id}) is None:
                    user_mongo.insert({'id': current_user.id, 'pic_bs64': pic_bs64})
                else:
                    user_mongo.update({'id': current_user.id}, {'$set': {'pic_bs64': pic_bs64}}, multi=True)
                    # os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    return jsonify({'url': file.filename})


@app.route('/blog/markdown/upload', methods=['POST', 'GET'])
@login_required
def blog_markdown_upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename[-2:].upper() == 'MD':
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
            # file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            with open(os.path.join(app.config['UPLOAD_FOLDER'], file.filename), "r", encoding='utf-8') as p:
                rs = ''
                for line in p.readlines():
                    rs += line
                blog.insert({'title': request.form['title'], 'content': rs})
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    return redirect(url_for('blog_add_markdown'))


@app.route('/blog/add/markdown', methods=['POST', 'GET'])
@login_required
def blog_add_markdown():
    return render_template('blog_add_markdown.html')


@app.route('/blog/download/<filename>')
def blog_download(filename):
    if request.method == 'GET':
        if os.path.isfile(os.path.join(app.root_path, UPLOAD_FOLDER, filename)):
            return send_from_directory(os.path.join(app.root_path, UPLOAD_FOLDER), filename, as_attachment=True)


@flask_login.user_logged_in.connect_via(app)
def _track_login(sender, user, **extra):
    user.login_count += 1
    user.last_login_ip = request.remote_addr
    mysql_db.session.add(user)
    mysql_db.session.commit()


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
    app.run()
