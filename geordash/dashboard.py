#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template, abort
from flask import current_app as app

from geordash.decorators import is_superuser
from geordash.checks.mapstore import get_resources_using_ows, get_name_from_ctxid
from geordash.api import get, gninternalid
from geordash.utils import find_localmduuid, unmunge

import json

dash_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard", template_folder='templates/dashboard')

def get_rescontent_from_resid(restype, resid):
    r = get(request, f'rest/geostore/data/{resid}', False)
    layers = dict()
    if r.status_code == 200:
        msmap = json.loads(r.content)
        if restype == 'MAP':
            llist = msmap['map']['layers']
        else:
            if 'map' not in msmap['mapConfig']:
                return dict()
            llist = msmap['mapConfig']['map']['layers']
        for l in llist:
            if 'group' not in l or ('group' in l and l['group'] != 'background'):
                if l['type'] in ('wms', 'wfs', 'wmts'):
                    layers[l['id']] = l
    return layers

@dash_bp.route("/")
def home():
    return render_template('home.html', reqhead=request.headers, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/csw/<string:portal>")
def csw(portal):
    # XXX for now only support the local GN
    localgn = app.extensions["conf"].get('localgn', 'urls')
    cswurl = '/' + localgn + '/' + portal + '/fre/csw'
    service = app.extensions["owscache"].get('csw', cswurl)
    if service.s is None:
        return abort(404)
    all_jobs_for_csw = app.extensions["rcli"].get_taskids_by_taskname_and_args('geordash.checks.csw.check_catalog',[cswurl])
    return render_template('csw.html', s=service, portal=portal, url=cswurl.replace('/', '~'), reqhead=request.headers, previous_jobs=all_jobs_for_csw, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/csw/<string:portal>/<string:uuid>")
def cswentry(portal, uuid):
    # XXX for now only support the local GN
    localgn = app.extensions["conf"].get('localgn', 'urls')
    cswurl = '/' + localgn + '/' + portal + '/fre/csw'
    service = app.extensions["owscache"].get('csw', cswurl)
    if service.s is None:
        return abort(404)
    if uuid not in service.contents():
        return abort(404)
    owslinks = list()
    r = service.contents()[uuid]
    gnid = gninternalid(uuid)
    for u in r.uris:
        if u['protocol'] in ('OGC:WMS', 'OGC:WFS'):
            stype = u['protocol'].split(':')[1].lower()
            url = u['url'].rstrip('?')
            localdomain = "https://" + app.extensions["conf"].get("domainName")
            if url.startswith(localdomain):
                url = url.removeprefix(localdomain)
            owslinks.append({'type': stype, 'url': url, 'layername': u['name'], 'descr': u['description']})
    all_jobs_for_cswrecord = app.extensions["rcli"].get_taskids_by_taskname_and_args('geordash.checks.csw.check_record',[cswurl, uuid])
    return render_template('cswentry.html', localgn=localgn, s=service, portal=portal, url=cswurl.replace('/', '~'), r=r, gnid=gnid, owslinks=owslinks, reqhead=request.headers, previous_jobs=all_jobs_for_cswrecord, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/ows/<string:stype>/<string:url>")
def ows(stype, url):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = app.extensions["owscache"].get(stype, url)
    if service.s is None:
        return abort(404)
    used_by = get_resources_using_ows(stype, url)
    all_jobs_for_ows = app.extensions["rcli"].get_taskids_by_taskname_and_args('geordash.checks.ows.owsservice',[stype, url])
    return render_template('ows.html', s=service, type=stype, url=url.replace('/', '~'), consumers=used_by, previous_jobs=all_jobs_for_ows, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/ows/<string:stype>/<string:url>/<string:lname>")
def owslayer(stype, url, lname):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = app.extensions["owscache"].get(stype, url)
    if service.s is None:
        return abort(404)
    # if a wfs from geoserver, prepend ws to lname
    if stype == 'wfs' and ':' not in lname and service.s.updateSequence and service.s.updateSequence.isdigit():
        ws = url.split('/')[-2]
        lname = f"{ws}:{lname}"
    if lname not in service.contents():
        return abort(404)
    localmduuids = find_localmduuid(service.s, lname)
    params = ""
    if not url.startswith('http') and stype == 'wms':
        bbox = service.contents()[lname].boundingBox
        params = "service=WMS&version=1.1.1&request=GetMap&styles=&format=application/openlayers&"
        params += f"srs={bbox[4]}&layers={lname}&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}&height=576&width=768"
    used_by = get_resources_using_ows(stype, url, lname)
    all_jobs_for_owslayer = app.extensions["rcli"].get_taskids_by_taskname_and_args('geordash.checks.ows.owslayer',[stype, url, lname])
    return render_template('owslayer.html', s=service, type=stype, url=url.replace('/','~'), lname=lname, consumers=used_by, previewqparams=params, localmduuids=localmduuids, previous_jobs=all_jobs_for_owslayer, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/map/<int:mapid>")
def map(mapid):
    all_jobs_for_mapid = app.extensions["rcli"].get_taskids_by_taskname_and_args('geordash.checks.mapstore.check_res', ["MAP", mapid])
    return render_template('map.html', mapid=mapid, layers=get_rescontent_from_resid("MAP", mapid), previous_jobs=all_jobs_for_mapid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/context/<int:ctxid>")
def ctx(ctxid):
    all_jobs_for_ctxid = app.extensions["rcli"].get_taskids_by_taskname_and_args('geordash.checks.mapstore.check_res', ["CONTEXT", ctxid])
    return render_template('ctx.html', ctxid=ctxid, ctxname=get_name_from_ctxid(ctxid), layers=get_rescontent_from_resid("CONTEXT", ctxid), previous_jobs=all_jobs_for_ctxid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())
