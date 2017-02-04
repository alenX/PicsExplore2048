# -*- coding: utf-8 -*-
from functools import wraps
from flask_login import current_user
from flask import  abort


def login_and_admin(func):
    @wraps(func)
    def login_admin_view(*args, **kwargs):
        if current_user is None or current_user.username != 'admin':
            print(current_user.username)
            abort(404)
        return func(*args, **kwargs)

    return login_admin_view
