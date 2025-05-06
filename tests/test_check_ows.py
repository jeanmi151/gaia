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

# configure a capabilities cache
from flask import Flask
from geordash.georchestraconfig import GeorchestraConfig
from geordash.owscapcache import OwsCapCache

c = OwsCapCache(GeorchestraConfig(), Flask(__name__))

# import the module we want to test
from geordash.checks.ows import owsservice, owslayer


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


def test_check_wms_service_works():
    # make sure the redis cache is empty
    c.forget("wms", "https://demo.georchestra.org/geoserver/bdtopo/ows")
    # fetch the capabilities in the local memory cache
    s = c.get("wms", "https://demo.georchestra.org/geoserver/bdtopo/ows")
    # queue a task checking all wms layers
    task = owsservice.delay("wms", "https://demo.georchestra.org/geoserver/bdtopo/ows")
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    assert result.state == "SUCCESS"
    assert type(result.result) == list
    # ensure result contains X tasks
    assert len(result.result[1]) > 10


def test_check_wfs_service_works():
    # make sure the redis cache is empty
    c.forget("wfs", "https://demo.georchestra.org/geoserver/bdtopo/ows")
    # fetch the capabilities in the local memory cache
    s = c.get("wfs", "https://demo.georchestra.org/geoserver/bdtopo/ows")
    # queue a task checking all wms layers
    task = owsservice.delay("wfs", "https://demo.georchestra.org/geoserver/bdtopo/ows")
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    assert result.state == "SUCCESS"
    assert type(result.result) == list
    # ensure result contains X tasks
    assert len(result.result[1]) > 10


def test_check_wms_layer_readtimeout():
    task = owslayer.delay(
        "wms", "https://geobretagne.fr/geoserver/costel/ows", "OS_2005_n1"
    )
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    # ensure result contains a readtimeout
    assert result.state == "SUCCESS"
    assert result.result["problems"][0]["e"] == "requests.exceptions.ReadTimeout"


def test_check_wfs_layer_parseerror():
    task = owslayer.delay(
        "wfs", "https://geobretagne.fr/geoserver/pnrgm/ows", "pnrgm:perimetre_pnrgm"
    )
    wait_for_task_completion(task.id)
    result = AsyncResult(task.id)
    # ensure result contains a parseerror
    assert result.state == "SUCCESS"
    assert result.result["problems"][0]["return"].startswith(
        "XML or text declaration not at start of entity"
    )
    assert result.result["problems"][0]["type"] == "ExpectedXML"


# when run standalone
if __name__ == "__main__":
    test_check_wms_service_works()
    test_check_wfs_service_works()
    test_check_wms_layer_readtimeout()
    test_check_wfs_layer_parseerror()
