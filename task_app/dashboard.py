#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template
from flask import current_app as app

from task_app.result_backend.redisbackend import RedisClient
from config import url

dash_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard", template_folder='templates/dashboard')

rcli = RedisClient(url)

@dash_bp.route("/")
def home():
    return render_template('home.html', reqhead=request.headers, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/map/<int:mapid>")
def map(mapid):
    all_jobs_for_mapid = rcli.get_taskids_by_taskname_and_args('task_app.checks.mapstore.check_res', ["MAP", mapid])
    return render_template('map.html', mapid=mapid, previous_jobs=all_jobs_for_mapid, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/context/<int:ctxid>")
def ctx(ctxid):
    return render_template('ctx.html', ctxid=ctxid, bootstrap=app.extensions["bootstrap"])
