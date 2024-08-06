#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template
from flask import current_app as app

dash_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard", template_folder='templates/dashboard')

@dash_bp.route("/")
def index() -> str:
    return render_template("index.html")

@dash_bp.route("/home")
def home():
    return render_template('home.html', reqhead=request.headers, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/map/<int:mapid>")
def map(mapid):
    return render_template('map.html', mapid=mapid, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/context/<int:ctxid>")
def ctx(ctxid):
    return render_template('ctx.html', ctxid=ctxid, bootstrap=app.extensions["bootstrap"])
