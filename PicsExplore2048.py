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
reds = redis.Redis(host='localhost', port=6379)
all_count = info.count()
reds.set('num', random.randint(1, all_count))


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/explore')
def explore_pic():
    return render_template('pics.html', pic_url='../static/image/225_133828_b3e21.jpg')


@app.route('/explore/next', methods=['POST'])
def explore_pic_next():
    print(reds.get('num'))
    reds.set('num', int(reds.get('num')) + 1)
    for i in info.find().limit(1).skip(int(reds.get('num'))):
        title = i['title']
        reds.set(title, title)
        with open(os.path.join(app.root_path + '/static/cache/image/', title), "wb") as t:
            t.write(base64.b64decode(i['bs64']))
            t.flush()
        return json.dumps('../static/cache/image/' + title)[1:-1]


@app.route('/explore/pre', methods=['POST'])
def explore_pic_pre():
    print(reds.get('num'))
    reds.set('num', int(reds.get('num')) - 1)
    for i in info.find().limit(1).skip(int(reds.get('num'))):
        title = i['title']
        with open(os.path.join(app.root_path + '/static/cache/image/', title), "wb") as t:
            t.write(base64.b64decode(i['bs64']))
            t.flush()
        return json.dumps('../static/cache/image/' + title)[1:-1]


if __name__ == '__main__':
    app.run()
