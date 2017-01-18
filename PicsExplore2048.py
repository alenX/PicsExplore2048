# -*- coding: utf-8 -*-
import base64
import json
import os
import pymongo
import random
import redis
from flask import Flask, render_template

app = Flask(__name__)
client = pymongo.MongoClient("localhost", 27017)
db = client['find_2048']
info = db["bs64_info"]
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
    pic_url = down_image()
    return json.dumps('../static/cache/image/' + pic_url)[1:-1]


@app.route('/explore/pre', methods=['POST'])
def explore_pic_pre():
    print(reds.get('num'))
    reds.set('num', int(reds.get('num')) - 1)
    pic_url = down_image()
    return json.dumps('../static/cache/image/' + pic_url)[1:-1]


def down_image():
    for i in info.find().limit(1).skip(int(int(reds.get('num')) % all_count) + 1):
        title = i['title']
        if reds.exists(title) == 0:  # 避免重复下载
            with open(os.path.join(app.root_path + '/static/cache/image/', title), "wb") as t:
                t.write(base64.b64decode(i['bs64']))
                t.flush()
            reds.set(str(title), str(title) + '')
        return title


if __name__ == '__main__':
    app.run()
