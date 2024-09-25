celery -A make_celery worker -P solo -B -E --loglevel INFO &
flask -A geordash run -h 0.0.0.0 -p 5002
