#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# allows to run the python file standalone
import sys

sys.path.append(".")

# import the module we want to test
from geordash.owscapcache import OwsCapCache


def init():
    # find the redisurl from toplevel's config.py
    import sys

    sys.path.append(".")
    import config

    from flask import Flask
    from geordash.georchestraconfig import GeorchestraConfig

    return OwsCapCache(GeorchestraConfig(), Flask(__name__))


def test_wfs_cache_reget_works():
    c = init()
    # cleanup
    c.forget("wfs", "/wxs/ows")
    s = c.get("wfs", "/wxs/ows")
    # check that there are layers
    assert len(s.contents()) > 0
    s2 = c.get("wfs", "/wxs/ows")
    assert s == s2
    # cleanup
    c.forget("wfs", "/wxs/ows")


def test_csw_update_redis():
    c = init()
    # cleanup
    c.forget("csw", "/geocat/atmo/fre/csw")
    s = c.get("csw", "/geocat/atmo/fre/csw")
    # ensure the cached entry has no records
    assert s.records == None
    assert (
        c.services["csw"]["https://ids.dev.craig.fr/geocat/atmo/fre/csw"].records
        == None
    )

    # fetch records
    assert len(s.contents()) == 2
    # persist them in redis
    s = c.get("csw", "/geocat/atmo/fre/csw")
    # forget the in-memory entry
    s.records = None
    # shouldnt refetch them, but get them from redis
    s2 = c.get("csw", "/geocat/atmo/fre/csw")
    assert len(s2.records) == 2
    # cleanup
    c.forget("csw", "/geocat/atmo/fre/csw")


# when run standalone
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)

    def get_logger(name):
        return logging.getLogger(name)

    test_csw_update_redis()
    test_wfs_cache_reget_works()
