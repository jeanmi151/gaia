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
            try:
                task = json.loads(v)
            except json.JSONDecodeError as e:
                print(f"discarding {k}, not json ? {e}")
                continue
            name = task["name"]
            args = task["args"]
            self.add_taskid_for_taskname_and_args(name, args, k.decode()[17:], task["date_done"])

    def get(self, key):
#        print(f"get({key}) called")
        if key[:17] == "celery-task-meta-" or key[:20] == "celery-taskset-meta-":
            return self.r.get(key)
        else:
            if isinstance(key, str):
                nk = "celery-task-meta-".encode() + key.encode()
            else:
                nk = "celery-task-meta-".encode() + key
            x = self.r.get(nk)
            if x is not None:
                return x
            else:
                if isinstance(key, str):
                    nk = "celery-taskset-meta-".encode() + key.encode()
                else:
                    nk = "celery-taskset-meta-".encode() + key
                return self.r.get(nk)

    def forget(self, taskid):
        v = self.get(taskid)
        if v is None:
            return None
        task = json.loads(v)
        taskname = None
        args = None
        if hasattr(task, 'name'):
            taskname = task["name"]
            args = task["args"]
        else:
            # taskset, take name & args from the first task of the set
            ftid = task['result'][1][0][0][0]
            tj = self.get(ftid)
            try:
                task = json.loads(tj)
            except json.JSONDecodeError as e:
                print(f"discarding {ftid}, not json ?")
                return None
            if task["name"].endswith('owslayer'):
                taskname = 'task_app.checks.ows.owsservice'
            args = task["args"][:-1]

        if taskname in self.task_by_taskname:
            if tuple(args) in self.task_by_taskname[taskname]:
                taskids = self.task_by_taskname[taskname][tuple(args)]
                for i in range(len(taskids)):
                    task = taskids[i]
                    if task["id"] == taskid:
                        taskids.remove(task)
                        return taskid

    def get_taskids_by_taskname_and_args(self, taskname, args):
        if taskname in self.task_by_taskname:
            if tuple(args) in self.task_by_taskname[taskname]:
                taskids = self.task_by_taskname[taskname][tuple(args)]
                for i in range(len(taskids)):
                    task = taskids[i]
                    # refresh finished ts from backend if not set
                    if task["finished"] is None:
                        v = self.get(task["id"])
                        taskb = json.loads(v)
                        if taskb["date_done"] is not None:
                            taskids[i] = { "id": task["id"], "finished": taskb["date_done"] }
                return taskids
        return None

    def add_taskid_for_taskname_and_args(self, taskname, args, taskid, finished=None):
        if taskname not in self.task_by_taskname:
            self.task_by_taskname[taskname] = dict()
        if tuple(args) not in self.task_by_taskname[taskname]:
            self.task_by_taskname[taskname][tuple(args)] = list()
        self.task_by_taskname[taskname][tuple(args)].append({ 'id': taskid, 'finished': finished})

if __name__ == '__main__':
    import sys
    sys.path.append('.')
    import config
    rc = RedisClient(config.url)
    print(rc.task_by_taskname["task_app.checks.mapstore.check_res"].keys())
    print(rc.task_by_taskname["task_app.checks.mapstore.check_res"][("CONTEXT", 38)])
    print(tuple(["CONTEXT", 38]) in rc.task_by_taskname["task_app.checks.mapstore.check_res"])
    print(len(rc.get("celery-task-meta-0cbc9aee-a2ea-4933-99b9-f448fb127044")))
    print(len(rc.get("0cbc9aee-a2ea-4933-99b9-f448fb127044")))
    print(len(rc.get("celery-task-meta-489dfd21-ad1a-4317-97da-af33d4111099")))
    tasks = rc.get_taskids_by_taskname_and_args("task_app.checks.mapstore.check_res", ["MAP", 1])
    print(tasks)
    for f in tasks:
        print(len(rc.get(f['id'])))
        print(f['finished'])
        j = json.loads(rc.get(f['id']))
        print(j["result"]["problems"])
