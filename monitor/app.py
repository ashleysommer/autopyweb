# -*- coding: utf-8 -*-
#
import os
from os import path
from sanic import Sanic
from sanic.response import text
from .functions import get_git_projects

app = Sanic(__name__)

@app.route("/list")
async def list(request):
    projs = get_git_projects(path.dirname(os.getcwd()))
    return text("ok", 200)

__all__ = ("app",)
