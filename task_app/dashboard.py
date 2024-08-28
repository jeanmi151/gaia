#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template
from flask import current_app as app

from task_app.result_backend.redisbackend import RedisClient
from task_app.decorators import is_superuser
from task_app.georchestraconfig import GeorchestraConfig
from task_app.owscapcache import OwsCapCache
from task_app.checks.mapstore import get_resources_using_ows, get_name_from_ctxid
from task_app.api import get

from config import url
import json

dash_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard", template_folder='templates/dashboard')

conf = GeorchestraConfig()
owscache = OwsCapCache(conf)
rcli = RedisClient(url)

def unmunge(url):
    """
    takes a munged url in the form ~geoserver(|~ws)~ows or http(s):~~fqdn~geoserver(|~ws)~ows
    returns: a proper url with slashes, eventually stripped of the local ids domainName (eg /geoserver/ws/ows)
    """
    url = url.replace('~','/')
    if not url.startswith('/') and not url.startswith('http'):
        url = '/' + url
    localdomain = "https://" + conf.get("domainName")
    if url.startswith(localdomain):
        url = url.removeprefix(localdomain)
    return url

def get_rescontent_from_resid(restype, resid):
    r = get(request, f'rest/geostore/data/{resid}', False)
    layers = dict()
    if r.status_code == 200:
        msmap = json.loads(r.content)
        if restype == 'MAP':
           llist = msmap['map']['layers']
        else:
           llist = msmap['mapConfig']['map']['layers']
        for l in llist:
            if 'group' not in l or ('group' in l and l['group'] != 'background'):
                if l['type'] in ('wms', 'wfs', 'wmts'):
                    layers[l['id']] = l
    return layers

@dash_bp.route("/")
def home():
    return render_template('home.html', reqhead=request.headers, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/ows/<string:stype>/<string:url>")
def ows(stype, url):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = owscache.get(stype, url)
    used_by = get_resources_using_ows(stype, url)
    return render_template('ows.html', s=service, type=stype, url=url.replace('/', '~'), consumers=used_by, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/ows/<string:stype>/<string:url>/<string:lname>")
def owslayer(stype, url, lname):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = owscache.get(stype, url)
    used_by = get_resources_using_ows(stype, url, lname)
    return render_template('owslayer.html', s=service, type=stype, url=url.replace('/','~'), lname=lname, consumers=used_by, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/map/<int:mapid>")
def map(mapid):
    all_jobs_for_mapid = rcli.get_taskids_by_taskname_and_args('task_app.checks.mapstore.check_res', ["MAP", mapid])
    return render_template('map.html', mapid=mapid, layers=get_rescontent_from_resid("MAP", mapid), previous_jobs=all_jobs_for_mapid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/context/<int:ctxid>")
def ctx(ctxid):
    all_jobs_for_ctxid = rcli.get_taskids_by_taskname_and_args('task_app.checks.mapstore.check_res', ["CONTEXT", ctxid])
    return render_template('ctx.html', ctxid=ctxid, ctxname=get_name_from_ctxid(ctxid), layers=get_rescontent_from_resid("CONTEXT", ctxid), previous_jobs=all_jobs_for_ctxid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())
