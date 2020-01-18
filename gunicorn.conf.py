#!/usr/bin/env python3
#
from sanic.worker import GunicornWorker

bind = "127.0.0.1:8000"
threads = 1
workers = 2
worker_class = "sanic.worker.GunicornWorker"
pid = "./gunicorn.pid"
keepalive = 5
timeout = 60
