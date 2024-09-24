#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery import Celery
from celery import Task
from flask import Flask
from flask import render_template
from flask_bootstrap import Bootstrap5
from task_app.events import CeleryEventsHandler
from task_app.owscapcache import OwsCapCache
from task_app.georchestraconfig import GeorchestraConfig
import threading

# this celery app object is used by the beat and worker threads
capp = Celery(__name__)
capp.config_from_object('task_app.celeryconfig')
capp.set_default()

from datetime import datetime, date, time
def format_datetime(value, format="%d %b %Y %I:%M %p"):
    """Format a date time to (Default): d Mon YYYY HH:MM P"""
    if value is None:
        return ""
    if  isinstance(value, float):
        return datetime.fromtimestamp(value).strftime(format)
    if  isinstance(value, str):
        return datetime.fromtimestamp(int(value)).strftime(format)
    return value.strftime(format)

def create_app() -> Flask:
    app = Flask(__name__, static_url_path='/dashboard/static')
    app.jinja_env.filters['datetimeformat'] = format_datetime
    app.config.from_mapping(
        CELERY=capp.conf
    )
    # cant work since its at /bootstrap and cant be below /dashboard ?
    # app.config.update(BOOTSTRAP_SERVE_LOCAL=True)
    app.config.from_prefixed_env()
    # needs FLASK_DEBUG in the env, or flask --debug
    # app.config.update(EXPLAIN_TEMPLATE_LOADING=True)
    app.extensions["bootstrap"] = Bootstrap5(app)
    celery_init_app(app)

    conf = GeorchestraConfig()
    app.extensions["conf"] = conf
    app.extensions["owscache"] = OwsCapCache(conf)
    from . import views, api, admin, dashboard

    dashboard.dash_bp.register_blueprint(views.tasks_bp)
    dashboard.dash_bp.register_blueprint(api.api_bp)
    dashboard.dash_bp.register_blueprint(admin.admin_bp)
    app.register_blueprint(dashboard.dash_bp)
    return app

def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    events_handler = CeleryEventsHandler(celery_app)
    evht = threading.Thread(name='evh',target=events_handler.start_listening, daemon=True)
    evht.start()
    return celery_app
