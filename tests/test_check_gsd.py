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
    assert(type(gsd.version) == int)

def test_check_single_datastore():
    # force-forget existing cache
    c.rediscli.delete("geoserver_datadir")
    c.services['geoserver_datadir'] = None
    # queue a task checking the first datastore
    task = gsdatadir_item.delay('datastore', 'DataStoreInfoImpl-51d47a63:192666818c2:-28c8')
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    assert result.state == "SUCCESS"


def test_check_datadir():
    task = gsdatadir.delay()
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    assert result.state == "SUCCESS"

# when run standalone
if __name__ == "__main__":
    test_get_gsd_view()
    test_check_single_datastore()
    test_check_datadir()
