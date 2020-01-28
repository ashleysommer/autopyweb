# -*- coding: utf-8 -*-
#
import os
import sys
from os import path
from sanic import Sanic  # type: ignore
from sanic.exceptions import SanicException, ServerError  # type: ignore
from sanic.response import text, json  # type: ignore
from typing import Optional

if __name__ == "__main__":
    print(
        " AutoPyWeb is a module, not a script. To run it, make a py file and import it and run it, like this:"
        "\n from autopyweb import app"
        "\n app.run()"
        "\n "
        "\n OR "
        "\n "
        "\n From the command line, run:"
        "\n $> python3 -m autopyweb"
    )
    sys.exit(1)

from .functions import get_git_projects, add_git_project, setup_python_project  # noqa: E402

app = Sanic(__name__)
app.config["RESPONSE_TIMEOUT"] = 318  # (two seconds before Gunicorn worker times out)


TRUTHS = (True, 1, "t", "T", "1", "true", "TRUE", "True")


class MissingParameter(SanicException):
    def __init__(self, param):
        message = "InvalidUsage. Missing parameter: {}".format(str(param))
        super(MissingParameter, self).__init__(message, 400)


class InvalidParameter(SanicException):
    def __init__(self, param):
        message = "InvalidUsage. Invalid parameter: {}".format(str(param))
        super(InvalidParameter, self).__init__(message, 400)


def wrap_exception(exc):
    if isinstance(exc, SanicException):
        return exc
    args = getattr(exc, "args", [])
    message = repr(exc)
    if args:
        try:
            next_line = str(args[0])
            message = message + "\n" + next_line
        except IndexError:
            pass
        try:
            next_line = args[1]
            message = message + "\n" + next_line
        except IndexError:
            pass
    return ServerError(message=message)


@app.route("/list")
async def list(request):
    projs = get_git_projects(path.dirname(os.getcwd()))
    for proj in projs:
        print(proj.active_branch)
    return text("ok", 200)


@app.post("/add")
async def add(request):
    origin_endpoint = next(iter(request.args.getlist("origin", [None])))
    if origin_endpoint is None:
        raise MissingParameter("origin")
    maybe_tag = next(iter(request.args.getlist("tag", [None])))
    maybe_branch = next(iter(request.args.getlist("branch", [None])))
    maybe_commit = next(iter(request.args.getlist("commit", [None])))
    maybe_dirname = next(iter(request.args.getlist("dirname", [None])))
    maybe_update = next(iter(request.args.getlist("update", [False])))
    do_update = maybe_update in TRUTHS

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
        "tag": maybe_tag,
        "branch": maybe_branch,
        "commit": maybe_commit,
        "dirname": maybe_dirname,
        "do_update": do_update,
    }
    try:
        print("adding git project to filesystem: {}".format(str(origin_endpoint)))
        project_path = add_git_project(path.dirname(os.getcwd()), origin_endpoint, **kwargs)
        print("finished add git project: {}".format(str(origin_endpoint)))
    except Exception as e:
        raise wrap_exception(e)
    try:
        print("Setting up project: {}".format(str(project_path)))
        success = setup_python_project(project_path)
        print("Done set up project.")
    except Exception as e:
        raise wrap_exception(e)
    return json({"success": success})


def run(host: Optional[str] = None, port: Optional[int] = None, debug: bool = False, **kwargs):
    """
    A shortcut for app.run()
    Needed because the file is called `app` and the app variable is called `app`.

    :return:
    """
    app.run(host=host, port=port, debug=debug, **kwargs)


__all__ = ("app", "run")
