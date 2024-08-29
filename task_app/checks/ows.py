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
