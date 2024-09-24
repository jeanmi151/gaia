#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from owslib.wms import WebMapService
from owslib.wfs import WebFeatureService
from owslib.wmts import WebMapTileService
from owslib.csw import CatalogueServiceWeb
from owslib.fes import PropertyIsEqualTo, And
from owslib.util import ServiceException
from requests.exceptions import HTTPError, SSLError, ReadTimeout
from urllib3.exceptions import MaxRetryError
from lxml.etree import XMLSyntaxError
from time import time

from redis import Redis
import jsonpickle
import json

from celery.utils.log import get_task_logger

tasklogger = get_task_logger(__name__)
is_dataset = PropertyIsEqualTo("Type", "dataset")
non_harvested = PropertyIsEqualTo("isHarvested", "false")

class CachedEntry:
    def __init__(self, stype, url):
        self.stype = stype
        self.url = url
        self.s = None
        self.records = None
        self.timestamp = None
        self.exception = None

    def contents(self):
        if self.stype in ('wms', 'wmts', 'wfs'):
            return self.s.contents
        if self.stype == 'csw' and self.s is not None and self.records is None:
            self.records = dict()
            startpos = 0
            while True:
                self.s.getrecords2(
                    constraints=[And([non_harvested] + [is_dataset])],
                    startposition=startpos,
                    maxrecords=100
                )
                self.records |= self.s.records
#                tasklogger.debug(f"start = {startpos}, res={self.s.results}, returned {len(self.s.records)}, mds={len(self.records)}")
#                print(f"start = {startpos}, res={self.s.results}, returned {len(self.s.records)}, mds={len(self.records)}")
                startpos = self.s.results['nextrecord'] # len(mds) + 1
                if startpos > self.s.results['matches'] or startpos == 0:
                    break
#            tasklogger.info(f"cached {len(self.records)} csw records for {self.url}")
#            print(f"cached {len(self.records)} csw records for {self.url}")
        return self.records

""" poorman's in-memory capabilities cache
keep a timestamp for the last fetch, refresh every 12h by default, and
force-fetch on demand.
"""


class OwsCapCache:
    def __init__(self, conf, app):
        self.services = dict()
        self.cache_lifetime = 12 * 60 * 60
        from config import url
        self.rediscli = Redis.from_url(url)
        self.conf = conf

    def fetch(self, service_type, url):
        if service_type not in ("wms", "wmts", "wfs", "csw"):
            return None
        tasklogger.debug("fetching {} getcapabilities for {}".format(service_type, url))
        # check first in redis
        rkey = f"{service_type}-{url.replace('/','~')}"
        re = self.rediscli.get(rkey)
        if re:
            ce = jsonpickle.decode(json.loads(re.decode('utf-8')))
            # if found, only return fetched value from redis if ts is valid
            if ce.timestamp + self.cache_lifetime > time():
                return ce
        entry = CachedEntry(service_type, url)
        try:
            # XX consider passing parse_remote_metadata ?
            if service_type == "wms":
                entry.s = WebMapService(url, version="1.3.0")
            elif service_type == "wfs":
                entry.s = WebFeatureService(url, version="1.1.0")
            elif service_type == "csw":
                entry.s = CatalogueServiceWeb(url, timeout=60)
            elif service_type == "wmts":
                entry.s = WebMapTileService(url)
        except ServiceException as e:
            # XXX hack parses the 403 page returned by the s-p ?
            if type(e.args) == tuple and "interdit" in e.args[0]:
                tasklogger.warning("{} needs auth ?".format(url))
            else:
                tasklogger.error(f"failed loading {service_type} from {url}")
                tasklogger.error(e)
            entry.exception = e
            # cache the failure
            entry.s = None
#        except (HTTPError, SSLError, ReadTimeout, MaxRetryError, XMLSyntaxError, KeyError) as e:
        except Exception as e:
            tasklogger.error(f"failed loading {service_type} from {url}, exception catched: {type(e)}")
            tasklogger.error(e)
            entry.s = None
            # cache the failure
            entry.exception = e
        entry.timestamp = time()
        self.services[service_type][url] = entry
        # persist entry in redis
        json_entry = json.dumps(jsonpickle.encode(entry))
        self.rediscli.set(rkey, json_entry)
        return entry

    def get(self, service_type, url, force_fetch=False):
        # is a relative url, prepend https://domainName
        if not url.startswith("http"):
            url = "https://" + self.conf.get("domainName") + url
        if service_type not in self.services:
            self.services[service_type] = dict()
        if url not in self.services[service_type]:
            return self.fetch(service_type, url)
        else:
            if (
                self.services[service_type][url].timestamp + self.cache_lifetime
                > time()
                and not force_fetch
            ):
                if self.services[service_type][url].s == None:
                    tasklogger.warning(f"already got a {type(self.services[service_type][url].exception)} for {service_type} {url} in cache, returning cached failure")
                    return self.services[service_type][url]
                tasklogger.debug(
                    "returning {} getcapabilities from process in-memory cache for {}".format(
                        service_type, url
                    )
                )
                return self.services[service_type][url]
            return self.fetch(service_type, url)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    tasklogger = logging.getLogger(__name__)
    from georchestraconfig import GeorchestraConfig

    c = OwsCapCache(GeorchestraConfig())
    s = c.get("wfs", "/wxs/ows")
    print(s)
    s = c.get("wfs", "/wxs/ows")
    print(s)
