# -*- coding: utf-8 -*-
import base64
import os
import pymongo
import random
import redis
from PIL import Image
from flask import Flask, render_template, jsonify
from bson.objectid import ObjectId

app = Flask(__name__)
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


@app.route('/')
def hello_world():
    return 'Hello World!'


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
def blog_list(current):
    all_num = blog.count()
    if all_num % 2 == 0:
        pages = all_num // 2
    else:
        pages = all_num // 2 + 1
    all_blog = blog.find().limit(2).skip((current - 1) * 2)
    return render_template('blog_list.html', blogs=all_blog, pages=pages, current=current)


@app.route('/blog/detail/<string:blog_id>')
def blog_detail(blog_id):
    current_blog = blog.find_one({'_id': ObjectId(blog_id)}) #bson
    if current_blog is None:
        return render_template('404.html'), 404
    return render_template('blog_detail.html', current_blog=current_blog)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


def i_sub_str(i_str, s, e):
    return i_str[s:e]


if __name__ == '__main__':
    jinja_env.filters['i_sub_str'] = i_sub_str
    app.run()
