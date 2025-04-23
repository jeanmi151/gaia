#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
from celery.utils.log import get_task_logger
from flask import request, current_app as app
import logging


# wrapper to get the appropriate logger, depending if we're in a flask or celery context
def get_logger(name=__name__):
    if request:
        if name:
            logger = logging.getLogger(name)
        else:
            logger = app.logger
    else:
        logger = get_task_logger(name)
    return logger
