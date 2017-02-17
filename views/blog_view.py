# -*- coding: utf-8 -*-
import pymongo
import datetime
import os
import base64
import flask_login
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, Flask, json, send_from_directory
from werkzeug.utils import secure_filename
from bson import ObjectId
from flask_login import LoginManager, login_required
from decorator import login_and_admin
from ext import db as mysql_db
from models import User, Comment
from flask_login import login_user, logout_user, current_user
from blog_form import CommentForm

app = Flask(__name__)
app.config.from_object('config')
blog_v = Blueprint('blog', __name__, template_folder='templates')

client = pymongo.MongoClient("localhost", 27017)
db = client['find_2048']
blogs = client['blogs']
blog = blogs['blog']
user_mongo = blogs['user']
EVERY_NUM = 3  # 每页数量
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@blog_v.route('/blog/list/<int:current>')
def blog_list(current=1):
    all_num = blog.count()
    if all_num % EVERY_NUM == 0:
        pages = all_num // EVERY_NUM
    else:
        pages = all_num // EVERY_NUM + 1
    all_blog = blog.find().limit(EVERY_NUM).skip((current - 1) * EVERY_NUM)
    return render_template('blog_list.html', blogs=all_blog, pages=pages, current=current)


@blog_v.route('/blog/detail/<string:blog_id>')
def blog_detail(blog_id):
    cf = CommentForm()
    current_blog = blog.find_one({'_id': ObjectId(blog_id)})  # bson
    if current_blog is None:
        return redirect(url_for('blog.blog_list', current=1))
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

    comms = Comment.query.filter_by(comment_id=blog_id).all()
    return render_template('blog_detail.html', current_blog=current_blog, image=bs_pic,
                           time=datetime.datetime.now().strftime('%Y%m%d%H%M%S'), form=cf,comms=comms)


@blog_v.route('/blog/add')
@login_required
@login_and_admin
def blog_add():
    return render_template('blog_add.html')


@blog_v.route('/blog/add_content/', methods=['POST'])
def add_content():
    paras = request.get_data()
    data = json.loads(paras)
    data['datetime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ids = blog.insert(data)
    return jsonify({'id': str(ids)})


@blog_v.route('/blog/login')
def blog_login():
    if current_user.get_id():
        return redirect(url_for('blog.blog_list', current=1))
    return render_template('login.html')


@blog_v.route('/blog/logout')
@login_required
def blog_logout():
    logout_user()
    return redirect(url_for('blog.blog_list', current=1))


@blog_v.route('/blog/login/reg', methods=['POST'])
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


@blog_v.route('/blog/login/register', methods=['POST'])
def blog_login_register():
    paras = request.get_data()
    user_para = json.loads(paras)

    u = User()
    u.pwd = user_para['password']
    u.username = user_para['user']
    # print(User.query.filter_by(username='admin').all())
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


@blog_v.route('/blog/edit')
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


@blog_v.route('/blog/upload', methods=['POST', 'GET'])
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


@blog_v.route('/blog/markdown/upload', methods=['POST', 'GET'])
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
                blog.insert({'title': request.form['title'], 'content': rs,
                             'datetime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    return redirect(url_for('blog.blog_add_markdown'))


@blog_v.route('/blog/add/markdown', methods=['POST', 'GET'])
@login_required
def blog_add_markdown():
    return render_template('blog_add_markdown.html')


# @blog_v.route('/blog/download/<filename>')
# def blog_download(filename):
#     if request.method == 'GET':
#         if os.path.isfile(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename)):
#             return send_from_directory(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), filename,
#                                        as_attachment=True)


@flask_login.user_logged_in.connect_via(app)
def _track_login(sender, user, **extra):
    user.login_count += 1
    user.last_login_ip = request.remote_addr
    mysql_db.session.add(user)
    mysql_db.session.commit()


@blog_v.route('/blog/edit/delete')
def blog_edit_delete():
    blog_id = request.args['_id']
    try:
        blog.remove({'_id': ObjectId(blog_id)})
        return jsonify({'succ': '1'})
    except:
        return jsonify({'succ': '0'})


@blog_v.route('/blog/contact_me')
def blog_contact_me():
    return render_template('blog/blog_contact_me.html')


@blog_v.route('/blog/comment/add', methods=['post'])
def blog_comment_add():
    blog_id = request.args['blog_id']
    cf = CommentForm()
    comm = Comment()
    comm.comment = cf.comment.data
    comm.comment_userid = current_user.id
    comm.comment_time = datetime.datetime.now()
    comm.comment_id = blog_id
    comm.comment_username = current_user.username
    mysql_db.session.add(comm)
    mysql_db.session.commit()
    # 增加comment
    return redirect('/blog/detail/' + blog_id)
