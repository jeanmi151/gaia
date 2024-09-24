celery -A task_app worker -P solo -B -E --loglevel INFO &
flask -A task_app run -h 0.0.0.0 -p 5002
