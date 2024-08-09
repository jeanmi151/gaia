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

from celery import shared_task
from celery import Task
from celery.utils.log import get_task_logger
tasklogger = get_task_logger(__name__)
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

msc = MapstoreChecker()


@shared_task()
def check_res(rescat, resid):
    m = msc.session.query(msc.Resource).filter(and_(msc.Resource.category_id == msc.cat[rescat], msc.Resource.id == resid)).one()
    tasklogger.info("{} avec id {} a pour titre {}".format('la carte' if rescat == 'MAP' else 'le contexte', m.id, m.name))
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
                tasklogger.info('uses {} layer name {} from {} (id={})'.format(l['type'], l['name'], l['url'], l['id']))
                if l['type'] not in msc.ows_services:
                    msc.ows_services[l['type']] = dict()
                if l['url'] not in msc.ows_services[l['type']]:
                    msc.ows_services[l['type']][l['url']] = dict()
                if l['name'] not in msc.ows_services[l['type']][l['url']]:
                    msc.ows_services[l['type']][l['url']][l['name']] = set()
                msc.ows_services[l['type']][l['url']][l['name']].add((m.id))
            case '3dtiles':
                tasklogger.debug('uses {} from {} (id={})'.format(l['type'], l['url'], l['id']))
            case 'cog':
                tasklogger.debug(l)
            case 'empty':
                pass
            case 'osm':
                pass
            case _:
                tasklogger.debug(l)

    for k,v in msc.ows_services.items():
        for u,ls in v.items():
            # is a relative url, prepend https://domainName
            if not u.startswith('http'):
                u = 'https://' + msc.conf.get('domainName') + u
            tasklogger.debug("fetching {} getcapabilities for {}".format(k, u))
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
                    tasklogger.warning("{} needs auth ?".format(u))
                else:
                    tasklogger.error(e)
                # skip check since we didn't get a proper getcapabilities
                continue
            for l,m in ls.items():
                if l not in s.contents:
                    ret['problems'].append('layer {} referenced by map {} doesnt exist in {} service at {}'.format(l, m, k, u))
    return ret

# this task enqueues subtasks
# XXX test as a celery group
@shared_task()
def check_all_mapstore_res_subtasks():
    taskids = list()
    for rescat in ('MAP', 'CONTEXT'):
        res = msc.session.query(msc.Resource).filter(msc.Resource.category_id == msc.cat[rescat]).all()
        tasklogger.debug(f"found {len(res)} {rescat} objects in database")
        for r in res:
            result = check_res.delay(rescat,r.id)
            taskids.append(result.id)
    return taskids

@shared_task(bind=True)
def check_all_mapstore_res(self: Task):
    taskres = dict()
    for rescat in ('MAP', 'CONTEXT'):
        taskres[rescat] = dict()
        res = msc.session.query(msc.Resource).filter(msc.Resource.category_id == msc.cat[rescat]).all()
        i = 0
        total = len(res)
        for r in res:
            taskres[r.id] = check_res(rescat,r.id)
            i += 1
            self.update_state(state="PROGRESS", meta={"current": i, "total": total})
    return taskres
