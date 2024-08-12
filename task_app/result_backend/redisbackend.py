#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import redis
import json

class RedisClient:
    def __init__(self, url):
        self.r = redis.Redis.from_url(url)
        self.task_by_taskname = dict()
        for k in self.r.scan_iter("celery-task-meta-*"):
            v = self.get(k.decode())
            task = json.loads(v)
            name = task["name"]
            args = task["args"]
            if name not in self.task_by_taskname:
                self.task_by_taskname[name] = dict()
            if tuple(args) not in self.task_by_taskname[name]:
                self.task_by_taskname[name][tuple(args)] = list()
            self.task_by_taskname[name][tuple(args)].append(k.decode())

    def get(self, key):
#        print(f"get({key}) called")
        if key[:17] == "celery-task-meta-":
            return self.r.get(key)
        else:
            if isinstance(key, str):
                nk = "celery-task-meta-".encode() + key.encode()
            else:
                nk = "celery-task-meta-".encode() + key
            return self.r.get(nk)

    def get_taskids_by_taskname_and_args(self, taskname, args):
        if taskname in self.task_by_taskname:
            if tuple(args) in self.task_by_taskname[taskname]:
                return self.task_by_taskname[taskname][tuple(args)]
        return None

if __name__ == '__main__':
    import sys
    sys.path.append('.')
    import config
    rc = RedisClient(config.url)
    print(rc.task_by_taskname["task_app.checks.mapstore.check_res"].keys())
    print(rc.task_by_taskname["task_app.checks.mapstore.check_res"][("CONTEXT", 38)])
    print(tuple(["CONTEXT", 38]) in rc.task_by_taskname["task_app.checks.mapstore.check_res"])
    print(len(rc.get("celery-task-meta-bdb8cfe5-5bc4-4fba-9f8a-94fdd98660be")))
    print(len(rc.get("bdb8cfe5-5bc4-4fba-9f8a-94fdd98660be")))
    print(len(rc.get("celery-task-meta-489dfd21-ad1a-4317-97da-af33d4111099")))
    tasks = rc.get_taskids_by_taskname_and_args("task_app.checks.mapstore.check_res", ["MAP", 1])
    print(tasks)
    for f in tasks:
        print(len(rc.get(f)))
        j = json.loads(rc.get(f))
        print(j["result"]["problems"])
