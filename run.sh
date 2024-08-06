celery -A make_celery worker -P solo -B -E --loglevel INFO &
flask -A task_app run -p 5002
