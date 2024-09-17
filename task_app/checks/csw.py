#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from task_app.checks.mapstore import msc
from task_app.dashboard import unmunge
from owslib.fes import PropertyIsEqualTo, Not, Or, And
from owslib import namespaces
from celery import shared_task
from celery import group
from celery.utils.log import get_task_logger
tasklogger = get_task_logger(__name__)

is_dataset = PropertyIsEqualTo("Type", "dataset")
non_harvested = PropertyIsEqualTo("isHarvested", "false")

@shared_task()
def check_catalog(url):
    """
    Given an csw service url check all its records:
    - all its records point to existing ogc services/records
    - all the external links resolve
    :param url: the CatalogServiceWeb service url
    :return: the list of errors
    """
    taskslist = list()
    service = msc.owscache.get('csw', url)
    if service['service'] is None:
        return False

    csw = service['service']
    startpos = 0
    while True:
        csw.getrecords2(
            constraints=[And([non_harvested] + [is_dataset])],
            startposition=startpos,
            maxrecords=100
        )
        for uuid in csw.records:
            tasklists.append(check_record.s(uuid))
        tasklogger.debug(f"start = {startpos}, res={csw.results}, returned {len(csw.records)}")
        startpos = csw.results['nextrecord'] # len(mds) + 1
        if startpos > csw.results['matches']:
            break
    grouptask = group(taskslist)
    groupresult = grouptask.apply_async()
    groupresult.save()
    return groupresult

@shared_task()
def check_record(url, uuid):
    """
    Given an csw record check:
    - all the ogc links point to existing ogc services/layers
    - all the external links resolve
    :param service: the CatalogServiceWeb service object
    :param uuid: the record uuid
    :return: the list of errors
    """
    tasklogger.info(f"checking uuid {uuid} in csw {url}")
    ret = dict()
    ret['problems'] = list()
    service = msc.owscache.get('csw', url)
    if service['service'] is None:
        ret['problems'].append(f"{url} isnt a csw ?")
        return ret

    csw = service['service']
    csw.getrecordbyid([uuid])
    if len(csw.records) != 1:
        ret['problems'].append(f"no metadata with uuid {uuid} in {url}")
        return ret

    owslinks = list()
    r = csw.records[uuid]
    for u in r.uris:
        if u['protocol'] in ('OGC:WMS', 'OGC:WFS'):
            stype = u['protocol'].split(':')[1].lower()
            url = u['url'].rstrip('?')
            localdomain = "https://" + msc.conf.get("domainName")
            if url.startswith(localdomain):
                url = url.removeprefix(localdomain)
            owslinks.append({'type': stype, 'url': url, 'layername': u['name'], 'descr': u['description']})
    return owslinks
