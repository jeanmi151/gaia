# how to add a new check

## new file

if that's a new file where you create the tasks, it needs to be added to the list of imports in [celeryconfig.py](https://github.com/georchestra/gaia/blob/master/geordash/celeryconfig.py.example). This way, the celery worker will know where to import tasks. It also needs to be restarted everytime a task code is modified.

## single task

depending on the cases, adding a task needs at least:
- the task code, ex [`owslayer`](https://github.com/georchestra/gaia/blob/master/geordash/checks/ows.py#L85). It should return a dict with a list of `problems`, but it can also return other things you might want to display in the web interface.

- a route to trigger it, see for example [`check_owslayer`](https://github.com/georchestra/gaia/blob/master/geordash/views.py#L196)

that method should return the task id to the page so that it knows which task result to poll via the [`/result` route](https://github.com/georchestra/gaia/blob/master/geordash/views.py#L22)

that route should be called by the [`CheckRes` js method](https://github.com/georchestra/gaia/blob/master/geordash/static/js/script.js#L290) trigerred by a click on the [*check now* button](https://github.com/georchestra/gaia/blob/master/geordash/templates/dashboard/owslayer.html#L100)

- a route to display its results, see for example [`owslayer`](https://github.com/georchestra/gaia/blob/master/geordash/dashboard.py#L191)

## group task

a group task is a task iterating over a list of resources, and triggering a subtask for each resource. For example the [owsservice](https://github.com/georchestra/gaia/blob/master/geordash/checks/ows.py#L71) lauches an [`owslayer`] check on each layer in the given ogc service.

if adding a new one, code has to be added in some places to mark the relationship between the child and parent task type:
- in [`result()`](https://github.com/georchestra/gaia/blob/master/geordash/views.py#L33) method, which checks how to get the results from all the sub-tasks
- in [`get_taskset_details()`](https://github.com/georchestra/gaia/blob/master/geordash/result_backend/redisbackend.py#L125) when infers the parent task name from the subtask
- in [`forget()`](https://github.com/georchestra/gaia/blob/master/geordash/result_backend/redisbackend.py#L177) which drops all the subtasks when dropping a group task

## periodic task

if adding a new periodic task, a section with the task name and its args should be added to the `beat schedule` in [celeryconfig.py](https://github.com/georchestra/gaia/blob/master/geordash/celeryconfig.py.example#L30)

this will tell the worker to queue a task at the given *schedule*
