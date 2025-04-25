#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import current_app as app
from celery import shared_task
from geordash.logwrap import get_logger
from geordash.owscapcache import OwsCapCache

from owslib.fes import PropertyIsEqualTo, And

non_harvested = PropertyIsEqualTo("isHarvested", "false")


@shared_task(bind=True)
def get_records(self, portal):
    """
    fetch csw records in a background task
    """
    localgn = app.extensions["conf"].get("localgn", "urls")
    cswurl = "/" + localgn + "/" + portal + "/fre/csw"
    occ = app.extensions["owscache"]
    service = occ.get("csw", cswurl)

    # get the amount of records, mostly for logging
    service.s.getrecords2(constraints=[non_harvested], resulttype="hits")
    nrec = service.s.results["matches"]

    records = dict()
    startpos = 0
    while True:
        service.s.getrecords2(
            constraints=[non_harvested],
            esn="full",
            startposition=startpos,
            maxrecords=25,
        )
        startpos = service.s.results["nextrecord"]
        records |= service.s.records
        self.update_state(
            state="PROGRESS",
            meta={
                "current": startpos,
                "total": nrec,
            },
        )
        get_logger("CswFetch").debug(
            f"start = {startpos}, res={service.s.results}, returned {len(service.s.records)}, mds={len(records)}"
        )
        if startpos > service.s.results["matches"] or startpos == 0:
            break
    get_logger("CswFetch").info(f"fetched {len(records)} csw records over {nrec}")
    # update our in-memory cache
    service.records = records
    # persist entry with records in redis
    furl = "https://" + app.extensions["conf"].get("domainName") + cswurl
    rkey = f"csw-{furl.replace('/','~')}"
    occ.set_entry_in_redis(rkey, service)

    # return the amount of records actually cached
    return len(records)
