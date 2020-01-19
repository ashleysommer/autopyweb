# -*- coding: utf-8 -*-
#
import os
from os import path
from sanic import Sanic
from sanic.exceptions import SanicException
from sanic.response import text
from .functions import get_git_projects, add_git_project

app = Sanic(__name__)

class MissingParameter(SanicException):
    def __init__(self, param):
        message = "InvalidUsage. Missing parameter: {}".format(str(param))
        super().__init__(message, 400)

class InvalidParameter(SanicException):
    def __init__(self, param):
        message = "InvalidUsage. Invalid parameter: {}".format(str(param))
        super().__init__(message, 400)

@app.route("/list")
async def list(request):
    projs = get_git_projects(path.dirname(os.getcwd()))
    for proj in projs:
        print(proj.active_branch)
    return text("ok", 200)

@app.route("/add")
async def add(request):
    origin_endpoint = next(iter(request.args.getlist('origin', [None])))
    if origin_endpoint is None:
        raise MissingParameter("origin")
    maybe_tag = next(iter(request.args.getlist('tag', [None])))
    maybe_branch = next(iter(request.args.getlist('branch', [None])))
    maybe_commit = next(iter(request.args.getlist('commit', [None])))

    if not any({maybe_tag, maybe_branch, maybe_commit}):
        raise MissingParameter("tag or branch or commit")
    elif all({maybe_tag, maybe_branch, maybe_commit}):
        raise InvalidParameter("Cannot have all three tag and branch and commit parameters")
    elif all({maybe_tag, maybe_branch}):
        raise InvalidParameter("Cannot have both tag and branch parameters")
    elif all({maybe_branch, maybe_commit}):
        raise InvalidParameter("Cannot have both branch and commit parameters")
    elif all({maybe_commit, maybe_tag}):
        raise InvalidParameter("Cannot have both commit and tag parameters")
    kwargs = {
        'tag': maybe_tag,
        'branch': maybe_branch,
        'commit': maybe_commit
    }
    project_path = add_git_project(path.dirname(os.getcwd()), origin_endpoint, **kwargs)


__all__ = ("app",)
