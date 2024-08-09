#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery.result import AsyncResult
from flask import Blueprint
from flask import request
from flask import jsonify

from . import tasks
from task_app.checks.mapstore import check_res, check_all_mapstore_res, check_all_mapstore_res_subtasks

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

@tasks_bp.get("/result/<id>")
def result(id: str) -> dict[str, object]:
    result = AsyncResult(id)
    ready = result.ready()
    return {
        "ready": ready,
        "successful": result.successful() if ready else None,
        "value": result.get() if ready else result.result,
    }


@tasks_bp.post("/add")
def add() -> dict[str, object]:
    a = request.form.get("a", type=int)
    b = request.form.get("b", type=int)
    result = tasks.add.delay(a, b)
    return {"result_id": result.id}


@tasks_bp.post("/block")
def block() -> dict[str, object]:
    result = tasks.block.delay()
    return {"result_id": result.id}


@tasks_bp.post("/process")
def process() -> dict[str, object]:
    result = tasks.process.delay(total=request.form.get("total", type=int))
    return {"result_id": result.id}

@tasks_bp.route("/check/map/<int:mapid>.json")
def check_map(mapid):
    result = check_res.delay('MAP',mapid)
    return {"result_id": result.id}

@tasks_bp.route("/check/context/<int:ctxid>.json")
def check_ctx(ctxid):
    result = check_res.delay('CONTEXT',ctxid)
    return {"result_id": result.id}

@tasks_bp.route("/check/mapstore", methods=['GET', 'POST'])
def check_mapstore():
    as_subtasks = request.args.get("subtasks", default=0, type=int)
    if as_subtasks != 0:
        result = check_all_mapstore_res.delay_subtasks()
    else:
        result = check_all_mapstore_res.delay()
    return {"result_id": result.id}
