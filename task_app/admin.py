#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template
from flask import current_app as app

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder='templates')

@admin_bp.route("/")
def index() -> str:
    # cf https://github.com/pallets/flask/issues/1361
    # and https://flask.palletsprojects.com/en/3.0.x/blueprints/#templates
    return render_template("admin/index.html")
