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
from celery import Celery
from celery.result import AsyncResult

# import the module we want to test
from geordash.tasks.fetch_csw import get_records


# XXX needs a running worker
def test_get_records_works():
    from flask import Flask
    from geordash.georchestraconfig import GeorchestraConfig
    from geordash.owscapcache import OwsCapCache

    c = OwsCapCache(GeorchestraConfig(), Flask(__name__))

    # configure a celery client
    app = Celery()
    app.conf.update(broker_url=config.url, result_backend=config.url)

    # make sure the redis cache is empty
    c.forget("csw", "/geocat/srv/fre/csw")
    # fetch the capabilities in the local memory cache, but *not* the records
    s = c.get("csw", "/geocat/srv/fre/csw")
    # queue a task fetching all records
    task = get_records.delay("srv")
    while True:
        result = AsyncResult(task.id)
        get_logger("FetchCsw").debug(
            f"task {task.id} state {result.state}, current result {result.result}"
        )
        if (
            result.state != "STARTED"
            and result.state != "PROGRESS"
            and result.state != "PENDING"
        ):
            break
        sleep(1)

    # leave some time to the worker to update redis
    sleep(3)
    # ensure the records are now cached
    s = c.get("csw", "/geocat/srv/fre/csw")
    get_logger("FetchCsw").debug(
        f"found {s.records} entries in local cache, task returned {result.result}"
    )
    assert len(s.records) == result.result


# when run standalone
if __name__ == "__main__":
    test_get_records_works()
