#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery.result import AsyncResult, GroupResult
from celery import group
from flask import Blueprint
from flask import request
from flask import jsonify

from task_app.dashboard import rcli, unmunge, owscache
from task_app.checks.mapstore import check_res, check_configs, check_resources
import task_app.checks.ows
from task_app.decorators import check_role

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

@tasks_bp.get("/result/<id>")
def result(id: str) -> dict[str, object]:
    result = GroupResult.restore(id)
    finished = None
    value = None
    completed = None
    if result is None:
        result = AsyncResult(id)
        # date_done is a datetime
        finished = result.date_done
        value = result.get() if result.ready() else result.result
    else:
        completed = f"{result.completed_count()} / {len(result.children)}"
        if result.ready():
            value = list()
            for r in result.results:
                # args are 'realized' only when all jobs are triggered
                # so might aswell do it when everything is done
                rcli.add_taskid_for_taskname_and_args(r.name, r.args, r.id)
                value.append({'args': r.args, 'problems': r.get()['problems']})
    ready = result.ready()
    return {
        "ready": ready,
        "completed": completed,
        "task": result.name if hasattr(result,'name') else "grouptask",
        "finished": (finished.strftime('%s') if finished is not None else False),
        "args": result.args if hasattr(result,'args') else "grouptask",
        "successful": result.successful() if ready else None,
        "value": value,
    }

@tasks_bp.get("/forget/<id>")
@check_role(role='SUPERUSER')
def forget(id: str):
    # forget first in the revmap
    rcli.forget(id)
    result = GroupResult.restore(id)
    if result is None:
        result = AsyncResult(id)
    else:
        # delete taskset from redis
        result.delete()
    # if is a taskset, should also forget all subtasks
    result.forget()
    return jsonify("ok")

@tasks_bp.route("/check/mapstore/configs.json")
def check_mapstore_configs():
    result = check_configs.delay()
    if result.id:
        rcli.add_taskid_for_taskname_and_args('task_app.checks.mapstore.check_configs', [], result.id)
    return {"result_id": result.id}

@tasks_bp.route("/check/map/<int:mapid>.json")
def check_map(mapid):
    result = check_res.delay('MAP',mapid)
    if result.id:
        rcli.add_taskid_for_taskname_and_args('task_app.checks.mapstore.check_res', ["MAP", mapid], result.id)
    return {"result_id": result.id}

@tasks_bp.route("/check/context/<int:ctxid>.json")
def check_ctx(ctxid):
    result = check_res.delay('CONTEXT',ctxid)
    if result.id:
        rcli.add_taskid_for_taskname_and_args('task_app.checks.mapstore.check_res', ["CONTEXT", ctxid], result.id)
    return {"result_id": result.id}

@tasks_bp.route("/check/mapstore/resources.json")
def check_mapstore_resources():
    groupresult = check_resources()
    if groupresult.id:
        rcli.add_taskid_for_taskname_and_args('task_app.checks.mapstore.check_resources', [], groupresult.id)
    return {"result_id": groupresult.id}

@tasks_bp.route("/check/ows/<string:stype>/<string:url>/<string:lname>.json")
def check_owslayer(stype, url, lname):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = owscache.get(stype, url)
    if service is None:
        return abort(404)
    # if a wfs from geoserver, prepend ws to lname
    if stype == 'wfs' and ':' not in lname and service['service'].updateSequence and service['service'].updateSequence.isdigit():
        ws = url.split('/')[-2]
        lname = f"{ws}:{lname}"
    if lname not in service['service'].contents:
        return abort(404)
    result = task_app.checks.ows.owslayer.delay(stype, url, lname)
    if result.id:
        rcli.add_taskid_for_taskname_and_args('task_app.checks.ows.owslayer', [stype, url, lname], result.id)
    return {"result_id": result.id}

@tasks_bp.route("/check/owsservice/<string:stype>/<string:url>.json")
def check_owsservice(stype, url):
    if stype not in ('wms', 'wmts', 'wfs'):
        return abort(412)
    url = unmunge(url)
    service = owscache.get(stype, url)
    if service is None:
        return abort(404)
    taskslist = list()
    for lname in service['service'].contents:
        taskslist.append(task_app.checks.ows.owslayer.s(stype, url, lname))
    grouptask = group(taskslist)
    groupresult = grouptask.apply_async()
    groupresult.save()
    if groupresult.id:
        rcli.add_taskid_for_taskname_and_args('task_app.checks.ows.owsservice', [stype, url], groupresult.id)
    return {"result_id": groupresult.id}
