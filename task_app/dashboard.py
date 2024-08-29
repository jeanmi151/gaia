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

from owslib.fes import PropertyIsEqualTo, Not, Or, And

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
    service = owscache.get('csw', '/' + conf.get('localgn', 'urls') + '/srv/fre/csw')
    if service is None:
        return abort(404)
    csw = service["service"]
    csw.getrecordbyid([uuid])
    if len(csw.records) != 1:
        return abort(404)
    return render_template('cswentry.html', s=service, r=csw.records[uuid], reqhead=request.headers, bootstrap=app.extensions["bootstrap"])

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
    if lname not in service['service'].contents:
        return abort(404)
    localmduuids = set()
    localdomain = "https://" + conf.get("domainName")
    for m in service['service'].contents[lname].metadataUrls:
        mdurl = m['url']
        mdformat = m['format']
        if mdurl.startswith(localdomain):
            if mdformat == 'text/xml' and "formatters/xml" in mdurl:
            # XXX find the uuid in https://geobretagne.fr/geonetwork/srv/api/records/60c7177f-e4e0-48aa-922b-802f2c921efc/formatters/xml
                localmduuids.add(mdurl.split('/')[7])
            if mdformat == 'text/html' and "datahub/dataset" in mdurl:
            # XXX find the uuid in https://geobretagne.fr/datahub/dataset/60c7177f-e4e0-48aa-922b-802f2c921efc
                localmduuids.add(mdurl.split('/')[5])
            if mdformat == 'text/html' and "api/records" in mdurl:
            # XXX find the uuid in https://ids.craig.fr/geocat/srv/api/records/9c785908-004d-4ed9-95a6-bd2915da1f08
                localmduuids.add(mdurl.split('/')[7])
            if mdformat == 'text/html' and "catalog.search" in mdurl:
            # XXX find the uuid in https://ids.craig.fr/geocat/srv/fre/catalog.search#/metadata/e37c057b-5884-429b-8bec-5db0baef0ee1
                localmduuids.add(mdurl.split('/')[8])
    params = ""
    if not url.startswith('http') and stype == 'wms':
        bbox = service['service'].contents[lname].boundingBox
        params = "service=WMS&version=1.1.1&request=GetMap&styles=&format=application/openlayers&"
        params += f"srs={bbox[4]}&layers={lname}&bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}&height=576&width=768"
    used_by = get_resources_using_ows(stype, url, lname)
    return render_template('owslayer.html', s=service, type=stype, url=url.replace('/','~'), lname=lname, consumers=used_by, previewqparams=params, localmduuids=localmduuids, bootstrap=app.extensions["bootstrap"])

@dash_bp.route("/map/<int:mapid>")
def map(mapid):
    all_jobs_for_mapid = rcli.get_taskids_by_taskname_and_args('task_app.checks.mapstore.check_res', ["MAP", mapid])
    return render_template('map.html', mapid=mapid, layers=get_rescontent_from_resid("MAP", mapid), previous_jobs=all_jobs_for_mapid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@dash_bp.route("/context/<int:ctxid>")
def ctx(ctxid):
    all_jobs_for_ctxid = rcli.get_taskids_by_taskname_and_args('task_app.checks.mapstore.check_res', ["CONTEXT", ctxid])
    return render_template('ctx.html', ctxid=ctxid, ctxname=get_name_from_ctxid(ctxid), layers=get_rescontent_from_resid("CONTEXT", ctxid), previous_jobs=all_jobs_for_ctxid, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())
