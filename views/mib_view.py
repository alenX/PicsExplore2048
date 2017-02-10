# -*- coding: utf-8 -*-
import datetime
import os

import pymongo
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, current_app,Flask
from werkzeug.utils import secure_filename

app = Flask(__name__)

client = pymongo.MongoClient("localhost", 27017)
blogs = client['blogs']
mib_info = blogs['mib_info']

mib_v = Blueprint('mib', __name__, template_folder='templates')


@mib_v.route('/mib/index')
def mib_index():
    print('1234')
    return render_template('tools/mib_info.html')


@mib_v.route('/mib/upload', methods=['POST', 'GET'])
def mib_upload():
    if request.method == 'POST':
        files = request.files.getlist("file")
        for f in filter(lambda d: str(d.filename).endswith('.mib'), files):
            mib_file_name = f.filename
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(mib_file_name)))
            with open(os.path.join(app.config['UPLOAD_FOLDER'], mib_file_name), "r") as p:
                line = ''
                for mib in p.readlines():
                    s = mib[:-1]
                    if 'OBJECT-TYPE' in s:
                        if 'DESCRIPTION' in line.strip() and line.strip().startswith('zx'):
                            mib_line = line.strip()
                            mib_name = mib_line.split()[0]
                            mib_desc = mib_line.split('DESCRIPTION')[1].strip().split('"')[1]
                            mib_info.insert(
                                {'mib_name': mib_name, 'mib_desc': mib_desc, 'time': datetime.datetime.now()})
                        line = ''
                    line += s
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], mib_file_name))
    return redirect(url_for('mib_index'))


@mib_v.route('/mib/query', methods=['GET', 'POST'])
def mib_query():
    mib_name = request.form['mib_name']
    mib = mib_info.find_one({'mib_name': str(mib_name).strip()})
    if mib:
        return jsonify({'desc': mib['mib_desc']})
    return jsonify({'desc': '不存在该记录'})
