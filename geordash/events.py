#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery.utils.log import get_task_logger


class CeleryEventsHandler:
    def __init__(self, flask_app):
        self._app = flask_app.extensions["celery"]
        self.fapp = flask_app
        self.logger = get_task_logger("CeleryEventsHandler")
        self._state = self._app.events.State()

    def task_sent(self, event):
        self._state.event(event)
        task = self._state.tasks.get(event["uuid"])
        # XXX task.args is a string representing a tuple at that point, we need a proper tuple..
        args = eval(task.args)
        self.logger.info(
            f"got {event['type']} event, task id {task.id} named {task.name}, with args {args} ({type(args)})"
        )
        self.fapp.extensions["rcli"].add_taskid_for_taskname_and_args(
            task.name, list(args), task.id
        )

    def start_listening(self):
        # XXX should have a retry loop if connection drops
        with self._app.connection() as connection:
            recv = self._app.events.Receiver(
                connection,
                handlers={
                    "task-sent": self.task_sent,
                },
            )
            recv.capture(limit=None)
