#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from task_app.georchestraconfig import GeorchestraConfig
conf = GeorchestraConfig()

def find_localmduuid(service, layername):
    localmduuids = set()
    localdomain = "https://" + conf.get("domainName")
    l = service.contents[layername]
    # wmts doesnt have metadataUrls
    if not hasattr(l, 'metadataUrls'):
        return localmduuids
    for m in l.metadataUrls:
        mdurl = m['url']
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
    return localmduuids
