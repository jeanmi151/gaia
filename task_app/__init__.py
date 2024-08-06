#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from celery import Celery
from celery import Task
from flask import Flask
from flask import render_template
from flask_bootstrap import Bootstrap5

# this celery app object is used by the beat and worker threads
capp = Celery(__name__)
capp.config_from_object('task_app.celeryconfig')
capp.set_default()

def create_app() -> Flask:
    app = Flask(__name__, static_url_path='/dashboard/static')
    app.config.from_mapping(
        CELERY=capp.conf
    )
    app.config.from_prefixed_env()
    app.extensions["bootstrap"] = Bootstrap5(app)
    celery_init_app(app)

    from . import views, api, dashboard

    dashboard.dash_bp.register_blueprint(views.tasks_bp)
    dashboard.dash_bp.register_blueprint(api.api_bp)
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
    return celery_app
