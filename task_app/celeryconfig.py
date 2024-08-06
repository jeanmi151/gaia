from config import url
broker_url = url
result_backend = url
worker_concurrency = 1
#autoscale = 8,1
#imports = ('testcelery.tasks',)
#worker_pool = solo
# create the task entry in the backend when its started, not only when its finished
task_track_started = True
# debug print sql requests done to the backend
database_engine_options = {'echo': True}
# store task name etc in the backend https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
result_extended = True

beat_schedule = {
  'print-every-10-seconds': {
    'task': 'task_app.tasks.printmsg',
    'schedule': 10.0,
    'args': ['hello']
  }
}
