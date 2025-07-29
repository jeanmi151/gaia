#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# allows to run the python file standalone
import sys

sys.path.append(".")
import config

try:
    from geordash.logwrap import get_logger
except:
    import logging

    logging.basicConfig(level=logging.DEBUG)

    def get_logger(name):
        return logging.getLogger(name)


from time import sleep

# configure a celery client
from celery import Celery
from celery.result import AsyncResult

app = Celery()
app.conf.update(broker_url=config.url, result_backend=config.url)

from flask import Flask
from geordash.georchestraconfig import GeorchestraConfig
from geordash.owscapcache import OwsCapCache

c = OwsCapCache(GeorchestraConfig(), Flask(__name__))

# import the module we want to test
from geordash.checks.gsd import gsdatadir, gsdatadir_item


def wait_for_task_completion(taskid):
    while True:
        result = AsyncResult(taskid)
        get_logger("TestOws").debug(
            f"task {taskid} state {result.state}, current result {result.result}"
        )
        if (
            result.state != "STARTED"
            and result.state != "PROGRESS"
            and result.state != "PENDING"
        ):
            break
        sleep(1)


def test_get_gsd_view():
    gsd = c.get_geoserver_datadir_view()
    assert type(gsd.version) == int


def check_single_item(itemtype, itemid):
    # force-forget existing cache
    c.rediscli.delete("geoserver_datadir")
    c.services["geoserver_datadir"] = None
    # queue a task checking the given item
    task = gsdatadir_item.delay(itemtype, itemid)
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    assert result.state == "SUCCESS"


def test_check_datadir():
    task = gsdatadir.delay()
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    assert result.state == "SUCCESS"


def test_check_subset_of_items():
    for i in [
        (
            "featuretypes",
            "FeatureTypeInfoImpl--19799db4:196fd2b59d4:-7ffd",
        ),  # -> geopackage public/parcelles_ally
        ("datastores", "DataStoreInfoImpl-51d47a63:192666818c2:-28c8"),
        ("datastores", "DataStoreInfoImpl-7581aaf0:196fd6d0a41:-7eae"),  # -> geopackage
        (
            "datastores",
            "DataStoreInfoImpl-21032313:18bf2254dd6:-3fcb",
        ),  # -> directory of shapefile
        (
            "datastores",
            "DataStoreInfoImpl--138c48ab:181c7cdace7:-9fe",
        ),  # -> JNDI (eclext)
        (
            "coveragestores",
            "CoverageStoreInfoImpl-749831bb:18dd0fbce6e:-74f9",
        ),  # -> GeoTIFF
        (
            "coveragestores",
            "CoverageStoreInfoImpl-749831bb:18dd0fbce6e:-745e",
        ),  # -> ImageMosaic
    ]:
        check_single_item(i[0], i[1])


# when run standalone
if __name__ == "__main__":
    test_get_gsd_view()
    test_check_subset_of_items()
    test_check_datadir()
