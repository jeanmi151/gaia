#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import requests

from flask import current_app as app
from celery import shared_task
from celery import group
from geordash.logwrap import get_logger

@shared_task()
def check_catalog(url):
    """
    called by beat scheduler, or check_catalog() route in views
    Given an csw service url check all its records:
    - all its records point to existing ogc services/records
    - all the external links resolve
    :param url: the CatalogServiceWeb service url
    :return: the list of errors
    """
    taskslist = list()
    service = app.extensions["owscache"].get('csw', url)
    if service.s is None:
        return False

    # at that point, contents is populated
    for uuid in service.contents():
        print(uuid)
        taskslist.append(check_record.s(url, uuid))
    grouptask = group(taskslist)
    groupresult = grouptask.apply_async()
    groupresult.save()
    return groupresult

@shared_task()
def check_record(url, uuid, single=False):
    """
    Given an csw record check:
    - all the ogc links point to existing ogc services/layers
    - all the external links resolve
    :param service: the CatalogServiceWeb service object
    :param uuid: the record uuid
    :return: the list of errors
    """
    get_logger("CheckCsw").info(f"checking uuid {uuid} in csw {url}")
    ret = dict()
    ret['problems'] = list()
    service = app.extensions["owscache"].get('csw', url, single)
    if service.s is None:
        ret['problems'].append({'type':'OGCException', 'url': url, 'stype': 'csw', 'exception': str(type(service.exception)), 'exceptionstr': str(service.exception)})
        return ret

    csw = service.s
    csw.getrecordbyid([uuid])
    if len(csw.records) != 1:
        ret['problems'].append({'type': 'NoSuchMetadata', 'uuid': uuid, 'url': url})
        return ret

    # since we've just done a getrecordbyid we have the full view
    r = csw.records[uuid]
    hasvalidlink = False
    for u in r.uris:
        if u['protocol'] in ('OGC:WMS', 'OGC:WFS'):
            stype = u['protocol'].split(':')[1].lower()
            if u['url'] is None:
                ret['problems'].append({'type': 'EmptyUrl', 'protocol': u['protocol']})
            url = u['url'].rstrip('?')
            localdomain = "https://" + app.extensions["conf"].get("domainName")
            if url.startswith(localdomain):
                url = url.removeprefix(localdomain)
            lname = u['name']
            service = app.extensions["owscache"].get(stype, url)
            if service.s is None:
                ret['problems'].append({'type':'OGCException', 'url': url, 'stype': stype, 'exception': str(type(service.exception)), 'exceptionstr': str(service.exception)})
            else:
                if stype == 'wfs' and ':' not in lname and service.s.updateSequence and service.s.updateSequence.isdigit():
                    ws = url.split('/')[-2]
                    lname = f"{ws}:{lname}"
                    get_logger("CheckCsw").debug(f"modified lname for {lname}")
                if lname not in service.contents():
                    ret['problems'].append({'type':'NoSuchLayer', 'url': url, 'stype': stype, 'lname': lname})
                else:
                    hasvalidlink = True
                    get_logger("CheckCsw").debug(f"layer {lname} exists in {stype} service at {url}")
        else:
            if u['protocol'] != None and (u['protocol'].startswith('WWW:DOWNLOAD') or u['protocol'].startswith('WWW:LINK')) and (u['url'] != None and u['url'].startswith('http')):
                # check that the url exists
                try:
                    timeout = 5
                    if 'outputformat=shape-zip' in u['url'].lower():
                        timeout = 60
                    r = requests.head(u['url'], timeout = timeout)
                    if r.status_code != 200:
                        ret['problems'].append({'type': 'BrokenProtocolUrl', 'url': u['url'], 'protocol': u['protocol'], 'code': r.status_code})
                    else:
                        hasvalidlink = True
                    get_logger("CheckCsw").debug(f"{u['url']} -> {r.status_code}")
                except Exception as e:
                    ret['problems'].append({'type': 'ConnectionFailure', 'url': u['url'], 'exception': str(type(e)), 'exceptionstr': str(e)})
            elif u['protocol'] != None and u['url'] == None:
                    ret['problems'].append({'type': 'EmptyUrl', 'protocol': u['protocol']})
            else:
                get_logger("CheckCsw").debug(f"didnt try querying non-ogc non-http url as {u['protocol']} : {u['url']}")
    if not hasvalidlink:
        ret['problems'].append({'type': 'MdHasNoLinks'})
    return ret
