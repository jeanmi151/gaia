#!/bin/sh
. ./env
celery -A $CELERY_APP worker --loglevel $CELERY_LOGLEVEL $CELERY_OPTS -s celerybeat-schedule &
flask -A $FLASK_APP --debug run $FLASK_OPTS
