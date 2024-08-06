#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import time

from celery import shared_task
from celery.utils.log import get_task_logger
from celery import Task

mytasklogger = get_task_logger(__name__)

@shared_task(ignore_result=False)
def add(a: int, b: int) -> int:
    return a + b

@shared_task(bind=True)
def printmsg(self, arg) -> None:
    mytasklogger.info(f"for task {self.request.id} got arg '{arg}'")

@shared_task()
def block() -> None:
    time.sleep(5)


@shared_task(bind=True, ignore_result=False)
def process(self: Task, total: int) -> object:
    for i in range(total):
        self.update_state(state="PROGRESS", meta={"current": i + 1, "total": total})
        time.sleep(1)

    return {"current": total, "total": total}
