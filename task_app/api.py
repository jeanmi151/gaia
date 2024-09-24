#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, jsonify, abort
from flask import current_app as app
import requests
import json

api_bp = Blueprint("api", __name__, url_prefix="/api")

def get(request, url, accept_json = True):
    headers = { 'sec-proxy': 'true' }
    if accept_json:
        headers['Accept'] = 'application/json'
    if 'sec-username' in request.headers:
        headers['sec-username'] = request.headers.get('Sec-Username')
    if 'sec-roles' in request.headers:
        headers['sec-roles'] = request.headers.get('Sec-Roles')
    msurl = app.extensions["conf"].get('mapstore', 'secproxytargets')
    return requests.get(msurl + url, headers = headers)

@api_bp.route("/mapstore/maps.json")
def maps():
    maps = get(request, 'rest/geostore/extjs/search/category/MAP/***/thumbnail,details,featured?includeAttributes=true')
    if maps.status_code != 200:
        return str(maps.status_code)
    return maps.json()

@api_bp.route("/mapstore/contexts.json")
def contexts():
    maps = get(request, 'rest/geostore/extjs/search/category/CONTEXT/***/thumbnail,details,featured?includeAttributes=true')
    if maps.status_code != 200:
        return str(maps.status_code)
    return maps.json()

def gninternalid(uuid):
    gnurl = app.extensions["conf"].get(app.extensions["conf"].get('localgn', 'urls'), 'secproxytargets')
    query = { "size": 1,
              "_source": {"includes": ["id"]},
              "query": { "bool": { "must": [ { "query_string" : { "query": "uuid: " + uuid } }, { "terms": { "isTemplate": [ "y", "n" ] } }]}}
    }
    md = requests.post(gnurl + "srv/api/search/records/_search",
        json = query,
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'})
    if md.status_code != 200:
      return md.text
    rep = md.json()
    if len(rep['hits']['hits']) != 1:
        return None
    return rep['hits']['hits'][0]['_source']['id']

@api_bp.route("/geonetwork/metadatas.json")
def metadatas():
    # bail out early if user is not auth
    username = request.headers.get('Sec-Username','anonymous')
    if username == 'anonymous':
        return abort(403)
    gnurl = app.extensions["conf"].get(app.extensions["conf"].get('localgn', 'urls'), 'secproxytargets')
    preauth = requests.get(gnurl + "srv/api/me", headers={'Accept': 'application/json'})
    if preauth.status_code == 204:
      if 'XSRF-TOKEN' in preauth.cookies:
        me = requests.get(gnurl + "srv/api/me",
            cookies = preauth.cookies,
            headers = {'Accept': 'application/json', 'sec-proxy': 'true', 'sec-username': username, 'X-XSRF-TOKEN': preauth.cookies['XSRF-TOKEN']})
        if me.status_code != 200:
            return me.text
        else:
            if 'id' in me.json():
                query = { "size": 30,
                            "_source": {"includes": ["id", "documentStandard", "resourceTitleObject" ]},
                            "query": { "bool": { "must": [ { "query_string" : { "query": "owner: {}".format(me.json()['id']) } }, { "terms": { "isTemplate": [ "y", "n" ] } }]}}
                }
                md = requests.post(gnurl + "srv/api/search/records/_search",
                    json = query,
                    cookies = preauth.cookies,
                    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'sec-proxy': 'true', 'sec-username': username, 'X-XSRF-TOKEN': preauth.cookies['XSRF-TOKEN']})
                if md.status_code != 200:
                    return md.text
                rep = md.json()
                retval = list()
                for h in rep['hits']['hits']:
                    retval.append({ '_id':h['_id'], 'gnid': h['_source']['id'], 'title':h['_source']['resourceTitleObject']['default'] });
                return jsonify(retval)
    else:
        return preauth.status_code
