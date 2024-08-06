#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from sqlalchemy import create_engine, MetaData, inspect, select, or_, and_
from sqlalchemy.engine import URL
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
import json

from owslib.wms import WebMapService
from owslib.wfs import WebFeatureService
from owslib.wmts import WebMapTileService
from owslib.util import ServiceException

from task_app.georchestraconfig import GeorchestraConfig

# solves conflicts in relationship naming ?
def name_for_collection_relationship(base, local_cls, referred_cls, constraint):
    name = referred_cls.__name__.lower()
    local_table = local_cls.__table__
    #print("local_cls={}, local_table={}, referred_cls={}, will return name={}, constraint={}".format(local_cls, local_table, referred_cls, name, constraint))
    if name in local_table.columns:
        newname = name + "_"
        print(
            "Already detected name %s present.  using %s" %
            (name, newname))
        return newname
    return name

class MapstoreChecker():
    def __init__(self):
        self.ows_services=dict()
        self.conf = GeorchestraConfig()
        url = URL.create(
            drivername="postgresql",
            username=self.conf.get('pgsqlUser'),
            host=self.conf.get('pgsqlHost'),
            password=self.conf.get('pgsqlPassword'),
            database=self.conf.get('pgsqlDatabase')
        )

        engine = create_engine(url)

# these three lines perform the "database reflection" to analyze tables and relationships
        m = MetaData(schema=self.conf.get('pgsqlGeoStoreSchema','mapstoregeostore'))
        Base = automap_base(bind=engine, metadata=m)
        Base.prepare(autoload_with=engine,name_for_collection_relationship=name_for_collection_relationship)

        # there are many tables in the database but me only directly use those
        self.Resource = Base.classes.gs_resource
        Category = Base.classes.gs_category

        Session = sessionmaker(bind=engine)
        self.session = Session()

        categories = self.session.query(Category).all()
        self.cat = dict()
        for c in categories:
            self.cat[c.name] = c.id
    def check_res(self, rescat, resid):
        m = self.session.query(self.Resource).filter(and_(self.Resource.category_id == self.cat[rescat], self.Resource.id == resid)).one()
        print("{} avec id {} a pour titre {}".format('la carte' if m.category_id == self.cat[rescat] else 'le contexte', m.id, m.name))
        # gs_attribute is a list coming from the relationship between gs_resource and gs_attribute
        ret = dict()

        for a in m.gs_attribute:
            if a.name in ('owner', 'context', 'details', 'thumbnail'):
                if 'attribute' not in ret:
                    ret['attribute'] = dict()
                ret['attribute'][a.name] = a.attribute_text
        for s in m.gs_security:
            # in the ms2-geor project, an entry with username is the owner
            if s.username is not None:
                ret['owner'] = s.username
            if s.groupname is not None:
                if 'groups' not in ret:
                    ret['groups'] = dict()
                ret['groups'][s.groupname] = { 'canread': s.canread, 'canwrite': s.canwrite }

        # uses automapped attribute from relationship instead of a query
        data = json.loads(m.gs_stored_data[0].stored_data)
        ret['backgrounds'] = list()
        ret['problems'] = list()
        if rescat == 'MAP':
            ret['layers'] = data["map"]["layers"]
        else:
            ret['layers'] = data["mapConfig"]["map"]["layers"]
        for l in ret['layers']:
            if 'group' in l and l["group"] == 'background':
                ret['backgrounds'].append(l)
            match l['type']:
                case 'wms'|'wfs'|'wmts':
                    print('uses {} layer name {} from {} (id={})'.format(l['type'], l['name'], l['url'], l['id']))
                    if l['type'] not in self.ows_services:
                        self.ows_services[l['type']] = dict()
                    if l['url'] not in self.ows_services[l['type']]:
                        self.ows_services[l['type']][l['url']] = dict()
                    if l['name'] not in self.ows_services[l['type']][l['url']]:
                        self.ows_services[l['type']][l['url']][l['name']] = set()
                    self.ows_services[l['type']][l['url']][l['name']].add((m.id))
                case '3dtiles':
                    print('uses {} from {} (id={})'.format(l['type'], l['url'], l['id']))
                case 'cog':
                    print(l)
                case 'empty':
                    pass
                case 'osm':
                    pass
                case _:
                    print(l)

        for k,v in self.ows_services.items():
            for u,ls in v.items():
                # is a relative url, prepend https://domainName
                if not u.startswith('http'):
                    u = 'https://' + self.conf.get('domainName') + u
                print ("fetching {} getcapabilities for {}".format(k, u))
                try:
                    if k == 'wms':
                        s = WebMapService(u, version='1.3.0')
                    if k == 'wfs':
                        s = WebFeatureService(u, version='1.1.0')
                    if k == 'wmts':
                        s = WebMapTileService(u)
                except ServiceException as e:
                    # XXX hack parses the 403 page returned by the s-p ?
                    if 'interdit' in e.args[0]:
                        print("{} needs auth ?".format(u))
                    else:
                        print(e)
                    # skip check since we didn't get a proper getcapabilities
                    continue
                for l,m in ls.items():
                    if l not in s.contents:
                        ret['problems'].append('layer {} referenced by map {} doesnt exist in {} service at {}'.format(l, m, k, u))
        return ret
