# -*- coding: utf-8 -*-
from flask_wtf import FlaskForm
from wtforms import StringField


class CommentForm(FlaskForm):
    comment = StringField('comment')
