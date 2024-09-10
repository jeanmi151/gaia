#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template, abort
from flask import current_app as app

from task_app.result_backend.redisbackend import RedisClient
from task_app.decorators import is_superuser
from task_app.owscapcache import OwsCapCache
from task_app.checks.mapstore import get_resources_using_ows, get_name_from_ctxid
from task_app.api import get, gninternalid
from task_app.utils import find_localmduuid, conf

from owslib.fes import PropertyIsEqualTo, Not, Or, And

from config import url
import json

dash_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard", template_folder='templates/dashboard')

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

@dash_bp.route("/csw")
def csw():
    # XXX for now only support the local GN
    service = owscache.get('csw', '/' + conf.get('localgn', 'urls') + '/srv/fre/csw')
    if service is None:
        return abort(404)
    is_dataset = PropertyIsEqualTo("Type", "dataset")
    is_service = PropertyIsEqualTo("Type", "service")
    non_harvested = PropertyIsEqualTo("isHarvested", "false")
    # collect the list of records XXX should be done in the API to populate the page client-side
    startpos = 0
    mds = {}
    csw = service["service"]
    while True:
        csw.getrecords2(
            constraints=[And([non_harvested] + [is_dataset])],
            startposition=startpos,
            maxrecords=100
        )
        for uuid in csw.records:
            mds[uuid] = csw.records[uuid]
        print(f"start = {startpos}, res={csw.results}, returned {len(csw.records)} allmds={len(mds)}")
        startpos = csw.results['nextrecord'] # len(mds) + 1
        if startpos > csw.results['matches']:
            break
    return render_template('csw.html', s=service, r=mds, reqhead=request.headers, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/csw/<string:uuid>")
def cswentry(uuid):
    # XXX for now only support the local GN
    localgn = conf.get('localgn', 'urls')
    service = owscache.get('csw', '/' + localgn + '/srv/fre/csw')
    if service is None:
        return abort(404)
    csw = service["service"]
    csw.getrecordbyid([uuid])
    if len(csw.records) != 1:
        return abort(404)
    owslinks = list()
    r = csw.records[uuid]
    gnid = gninternalid(uuid)
    for u in r.uris:
        if u['protocol'] in ('OGC:WMS', 'OGC:WFS'):
            stype = u['protocol'].split(':')[1].lower()
            url = u['url'].rstrip('?')
            localdomain = "https://" + conf.get("domainName")
            if url.startswith(localdomain):
                url = url.removeprefix(localdomain)
            owslinks.append({'type': stype, 'url': url, 'layername': u['name'], 'descr': u['description']})
    return render_template('cswentry.html', localgn=localgn, s=service, r=r, gnid=gnid, owslinks=owslinks, reqhead=request.headers, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/ows/<string:stype>/<string:url>")
def ows(stype, url):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = owscache.get(stype, url)
    if service is None:
        return abort(404)
    used_by = get_resources_using_ows(stype, url)
    return render_template('ows.html', s=service, type=stype, url=url.replace('/', '~'), consumers=used_by, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/ows/<string:stype>/<string:url>/<string:lname>")
def owslayer(stype, url, lname):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = owscache.get(stype, url)
    if service is None:
        return abort(404)
    # if a wfs from geoserver, prepend ws to lname
    if stype == 'wfs' and ':' not in lname and service['service'].updateSequence and service['service'].updateSequence.isdigit():
        ws = url.split('/')[-2]
        lname = f"{ws}:{lname}"
    if lname not in service['service'].contents:
        return abort(404)
    localmduuids = find_localmduuid(service['service'], lname)
    params = ""
    if not url.startswith('http') and stype == 'wms':
        bbox = service['service'].contents[lname].boundingBox
        params = "service=WMS&version=1.1.1&request=GetMap&styles=&format=application/openlayers&"
        params += f"srs={bbox[4]}&layers={lname}&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}&height=576&width=768"
    used_by = get_resources_using_ows(stype, url, lname)
    all_jobs_for_owslayer = rcli.get_taskids_by_taskname_and_args('task_app.checks.ows.owslayer',[stype, url, lname])
    return render_template('owslayer.html', s=service, type=stype, url=url.replace('/','~'), lname=lname, consumers=used_by, previewqparams=params, localmduuids=localmduuids, previous_jobs=all_jobs_for_owslayer, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/map/<int:mapid>")
def map(mapid):
    all_jobs_for_mapid = rcli.get_taskids_by_taskname_and_args('task_app.checks.mapstore.check_res', ["MAP", mapid])
    return render_template('map.html', mapid=mapid, layers=get_rescontent_from_resid("MAP", mapid), previous_jobs=all_jobs_for_mapid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/context/<int:ctxid>")
def ctx(ctxid):
    all_jobs_for_ctxid = rcli.get_taskids_by_taskname_and_args('task_app.checks.mapstore.check_res', ["CONTEXT", ctxid])
    return render_template('ctx.html', ctxid=ctxid, ctxname=get_name_from_ctxid(ctxid), layers=get_rescontent_from_resid("CONTEXT", ctxid), previous_jobs=all_jobs_for_ctxid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())
