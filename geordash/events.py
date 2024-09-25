#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from geordash.dashboard import rcli

class CeleryEventsHandler:
    def __init__(self, celery_app):
        self._app = celery_app
        self._state = celery_app.events.State()

    def task_sent(self, event):
        self._state.event(event)
        task = self._state.tasks.get(event['uuid'])
        # XXX task.args is a string representing a tuple at that point, we need a proper tuple..
        args = eval(task.args)
#        print(f"got {event['type']} event, task id {task.id} named {task.name}, with args {args} ({type(args)})")
        rcli.add_taskid_for_taskname_and_args(task.name, list(args), task.id)

    def start_listening(self):
        print('start listening for celery events')
        # XXX should have a retry loop if connection drops
        with self._app.connection() as connection:
            recv = self._app.events.Receiver(connection, handlers={
                'task-sent': self.task_sent,
            })
            recv.capture(limit=None)
