#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from owslib.wms import WebMapService
from owslib.wfs import WebFeatureService
from owslib.wmts import WebMapTileService
from owslib.csw import CatalogueServiceWeb
from owslib.util import ServiceException
from requests.exceptions import HTTPError, SSLError, ReadTimeout
from urllib3.exceptions import MaxRetryError
from lxml.etree import XMLSyntaxError
from time import time

from celery.utils.log import get_task_logger

tasklogger = get_task_logger(__name__)

""" poorman's in-memory capabilities cache
keep a timestamp for the last fetch, refresh every 12h by default, and
force-fetch on demand.
"""


class OwsCapCache:
    def __init__(self, conf):
        self.services = dict()
        self.cache_lifetime = 12 * 60 * 60
        self.conf = conf

    def fetch(self, service_type, url):
        s = None
        if service_type not in ("wms", "wmts", "wfs", "csw"):
            return None
        tasklogger.debug("fetching {} getcapabilities for {}".format(service_type, url))
        entry = dict()
        try:
            if service_type == "wms":
                s = WebMapService(url, version="1.3.0")
            elif service_type == "wfs":
                s = WebFeatureService(url, version="1.1.0")
            elif service_type == "csw":
                s = CatalogueServiceWeb(url, timeout=60)
            elif service_type == "wmts":
                s = WebMapTileService(url)
            entry["service"] = s
        except ServiceException as e:
            # XXX hack parses the 403 page returned by the s-p ?
            if type(e.args) == tuple and "interdit" in e.args[0]:
                tasklogger.warning("{} needs auth ?".format(url))
            else:
                tasklogger.error(f"failed loading {service_type} from {url}")
                tasklogger.error(e)
            entry["exception"] = e
            # cache the failure
            entry["service"] = None
#        except (HTTPError, SSLError, ReadTimeout, MaxRetryError, XMLSyntaxError, KeyError) as e:
        except Exception as e:
            tasklogger.error(f"failed loading {service_type} from {url}, exception catched: {type(e)}")
            tasklogger.error(e)
            entry["service"] = None
            # cache the failure
            entry["exception"] = e
        entry["timestamp"] = time()
        self.services[service_type][url] = entry
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
                self.services[service_type][url]["timestamp"] + self.cache_lifetime
                > time()
                and not force_fetch
            ):
                if self.services[service_type][url]["service"] == None:
                    tasklogger.warning(f"already got a {type(self.services[service_type][url]['exception'])} for {service_type} {url} in cache, returning cached failure")
                    return self.services[service_type][url]
                tasklogger.debug(
                    "returning {} getcapabilities from cache for {}".format(
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
