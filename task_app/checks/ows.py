#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import requests

from celery import shared_task
from celery import Task
from celery.utils.log import get_task_logger
tasklogger = get_task_logger(__name__)

from task_app.checks.mapstore import msc
from task_app.dashboard import unmunge

import xml.etree.ElementTree as ET
from owslib.util import ServiceException

def find_tilematrix_center(wmts, lname):
    # find first tilematrixset
    # tilematrixset is a service attribute
    tsetk = list(wmts.tilematrixsets.keys())[0]
    tset = wmts.tilematrixsets[tsetk]
    # find last tilematrix level
    tmk = list(tset.tilematrix.keys())[-1]
    lasttilematrix = tset.tilematrix[tmk]
#    print(f"first tilematrixset named {tsetk}: {tset}")
#    print(f"last tilematrix lvl named {tmk}: {lasttilematrix} (type {type(lasttilematrix)}")
#    print(f"width={lasttilematrix.matrixwidth}, height={lasttilematrix.matrixheight}")
    # tilematrixsetlink is a layer attribute
    l = wmts.contents[lname]
    tms = list(l.tilematrixsetlinks.keys())[0]
#    print(f"first tilesetmatrixlink for layer {lname} named {tms}")
    tsetl = l.tilematrixsetlinks[tms]
    #geoserver/gwc sets tilematrixsetlinks, mapproxy doesnt
    if len(tsetl.tilematrixlimits) > 0:
        tmk = list(tsetl.tilematrixlimits.keys())[-1]
        tml = tsetl.tilematrixlimits[tmk]
        r = tml.mintilerow + int((tml.maxtilerow - tml.mintilerow) / 2)
        c = tml.mintilecol + int((tml.maxtilecol - tml.mintilecol) / 2)
    else:
        r = int(int(lasttilematrix.matrixwidth) / 2)
        c = int(int(lasttilematrix.matrixheight) / 2)
    return (tms, tmk, r, c)

def reduced_bbox(bbox):
    """
    for a layer bounding box, return a very small bbox at the center of it
    used for getmap/getfeature tests to ensure it doesn't hammer the remote
    """
    xmin, ymin, xmax, ymax = bbox
    return [xmin+0.49*(xmax-xmin),
         ymin+0.49*(ymax-ymin),
         xmax-0.49*(xmax-xmin),
         ymax-0.49*(ymax-ymin)]

@shared_task()
def owslayer(stype, url, layername):
    """
    Given an ows layer check that:
    - it refers to existing metadata ids
    - TODO: a getmap/getfeature query succeeds
    :param stype: the service type (wms/wfs/wmts)
    :param url: the service url
    :param layername: the layer name in the service object
    :return: the list of errors
    """
    tasklogger.info(f"checking layer {layername} in {stype} {url}")
    ret = dict()
    ret['problems'] = list()
    url = unmunge(url)
    service = msc.owscache.get(stype, url)
    localmduuids = set()
    localdomain = "https://" + msc.conf.get("domainName")
    # XXX for wfs, no metadataUrls are found by owslib, be it with 1.1.0 or 2.0.0 ?
    for m in service['service'].contents[layername].metadataUrls:
        mdurl = m['url']
        # check first that the url exists
        r = requests.head(mdurl)
        if r.status_code != 200:
            ret['problems'].append(f"metadataurl at {mdurl} doesn't seem to exist (returned code {r.status_code})")
        tasklogger.debug(f"{mdurl} -> {r.status_code}")
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
    # in a second time, make sure local md uuids are reachable via csw
    if len(localmduuids) > 0:
        localgn = msc.conf.get('localgn', 'urls')
        service = msc.owscache.get('csw', '/' + localgn + '/srv/fre/csw')
        csw = service['service']
        csw.getrecordbyid(list(localmduuids))
        tasklogger.debug(csw.records)
        for uuid in localmduuids:
            if uuid not in csw.records:
                ret['problems'].append(f"md with uuid {uuid} not found in local csw")
            else:
                tasklogger.debug(f"md with uuid {uuid} exists, title {csw.records[uuid].title}")

    return ret
