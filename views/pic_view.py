# -*- coding: utf-8 -*-
from flask import Flask, Blueprint, render_template, jsonify
import base64
from PIL import Image
import os
import redis
import pymongo
import random

client = pymongo.MongoClient("localhost", 27017)
db = client['find_2048']
info = db["bs64_info"]
# reds = redis.Redis(host='localhost', port=6379, db=0)
# reds.flushdb()
all_count = info.count()
# reds.set('num', random.randint(1, all_count))
app = Flask(__name__)
pic_v = Blueprint('pic', __name__, template_folder='templates')


@pic_v.route('/explore')
def explore_pic():
    pic_path = os.path.join(app.root_path + '../static/cache/image/')
    # for root, dirs, files in os.walk(pic_path):
    #     reds.set(files, files)
    return render_template('pics.html', pic_url='../static/image/225_133828_b3e21.jpg')


@pic_v.route('/explore/next', methods=['POST'])
def explore_pic_next():
    # reds.set('num', int(reds.get('num')) + 1)
    pics = down_image()
    return jsonify(pics)


@pic_v.route('/explore/pre', methods=['POST'])
def explore_pic_pre():
    # reds.set('num', int(reds.get('num')) - 1)
    pics = down_image()
    return jsonify(pics)


def down_image():
    for i in info.find().limit(1).skip(int(random.randint(0,all_count) % all_count) + 1):
        title = i['title']
        # if reds.exists(title) == 0:  # 避免重复下载
        #     with open(os.path.join(app.root_path + '/../static/cache/image/', title), "wb") as t:
        #         t.write(base64.b64decode(i['bs64']))
        #         t.flush()
        #     reds.set(str(title), str(title) + '')
        with open(os.path.join(app.root_path + '/../static/cache/image/', title), "wb") as t:
            t.write(base64.b64decode(i['bs64']))
            t.flush()
        p = Image.open(os.path.join(app.root_path + '/../static/cache/image/', title))
        return {'title': '../static/cache/image/' + title, 'height': p.size[0], 'width': p.size[1]}
