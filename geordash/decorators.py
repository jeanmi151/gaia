#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
from functools import wraps
from flask import request, abort, jsonify


def is_superuser():
    roles = request.headers.get("sec-roles", "").split(";")
    return "ROLE_SUPERUSER" in roles


def check_role(role, json=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_roles = request.headers.get("sec-roles", "").split(";")
            if "ROLE_" + role not in user_roles:
                if json:
                    return jsonify({"message": "not authorized"}), 403
                return abort(403)
            return func(*args, **kwargs)

        return wrapper

    return decorator
