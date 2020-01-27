# -*- coding: utf-8 -*-
#
import sys
from os import path, environ
import subprocess
import os
from git import Repo
from shutil import rmtree
import time

from pkg_resources import working_set
from setuptools.sandbox import save_pkg_resources_state, save_modules, setup_context, _execfile, DirectorySandbox


def debug_print(output, *args, **kwargs):
    print(output, *args, **kwargs)


def get_git_projects(location):
    location = path.abspath(location)
    contents = os.listdir(location)
    directories = [c for c in contents if path.isdir(c)]
    git_dirs = []
    for d in directories:
        full_d = path.join(location, d)
        d_contents = os.listdir(full_d)
        d_directories = [c for c in d_contents if path.isdir(c)]
        if ".git" in d_directories:
            git_dirs.append(full_d)
    debug_print("Found {} potential repo dirs. Now loading them in Repo classes.".format(str(len(git_dirs))))
    repos = []
    for d in git_dirs:
        try:
            r = Repo(d)
        except Exception as e:
            debug_print(e)
            debug_print("Not adding {}".format(d))
            continue
        repos.append(r)
    return repos


def guess_project_name(guess_string):
    if guess_string.startswith("https://"):
        guess_string = guess_string[8:]
    elif guess_string.startswith("http://"):
        guess_string = guess_string[7:]
    elif guess_string.startswith("ssh://"):
        guess_string = guess_string[6:]
    if guess_string.endswith("/browse"):
        guess_string = guess_string[:-7]
    if guess_string.endswith("/git"):
        guess_string = guess_string[:-4]
    if guess_string.endswith(".git"):
        guess_string = guess_string[:-4]
    split_parts = guess_string.split("/")
    split_parts = [s for s in split_parts if len(s)]
    return split_parts[-1]


def path_friendly(instring):
    instring = instring.replace("/", "")
    instring = instring.replace("_", "-")
    instring = instring.replace(".", "-")
    return instring


def add_git_project(location, origin_url, tag=None, branch=None, commit=None, dirname=None, do_update=False,
                    **kwargs):
    project_name = path_friendly(guess_project_name(origin_url))
    location = path.abspath(location)
    t = str(int(time.time()))
    bare_location = path.join(location, "bare-{}-{}".format(project_name, t))
    if path.isdir(bare_location):
        rmtree(bare_location)
    repo = Repo.init(bare_location, bare=True)
    try:
        REMOTE_NAME = "origin"
        origin_remote = repo.create_remote(REMOTE_NAME, origin_url)
        exists = origin_remote.exists()
        if not exists:
            raise RuntimeError("Origin does not exist: {}".format(origin_url))
        try:
            easy_refspec = "refs/heads/*:refs/remotes/{:s}/*".format(REMOTE_NAME)
            for fetch_info in origin_remote.fetch(easy_refspec):
                print("Updated {} to {}".format(fetch_info.ref, fetch_info.commit))
        except Exception:
            raise RuntimeError("Cannot fetch data from origin: {}".format(origin_url))
        if tag is not None:
            refspec = "+refs/tags/{t:s}:refs/remotes/{r:s}/{t:s}".format(t=str(tag), r=REMOTE_NAME)
            fetchs_found = origin_remote.fetch(refspec=refspec)
            if len(fetchs_found) < 1:
                raise RuntimeError("Tag not found on that origin: {:s}".format(branch))
            try:
                ref = repo.remotes[REMOTE_NAME].refs[str(tag)]
                ref_commit = ref.commit
                _dirname = "{:s}-tag-{:s}-{:s}".format(project_name, path_friendly(tag), str(ref_commit)[:7])
            except KeyError:
                raise RuntimeError("Tag not found on that origin: {}".format(tag))
        elif branch is not None:
            refspec = "+refs/heads/{h:s}:refs/remotes/{r:s}/{h:s}".format(h=branch, r=REMOTE_NAME)
            fetchs_found = origin_remote.fetch(refspec=refspec)
            if len(fetchs_found) < 1:
                raise RuntimeError("Branch not found on that origin: {:s}".format(branch))
            try:
                ref = repo.remotes[REMOTE_NAME].refs[str(branch)]
                ref_commit = ref.commit
                _dirname = "{:s}-br-{:s}-{:s}".format(project_name, path_friendly(branch), str(ref_commit)[:7])
            except KeyError:
                raise RuntimeError("Branch not found on that origin: {}".format(branch))
        elif commit is not None:
            raise NotImplementedError("Cannot yet fetch remote reference from just a commit id.")
            # try:
            #     ref = repo.remotes[REMOTE_NAME].refs[commit]
            #     _dirname = "sha-{:s}".format(ref.commit)
            # except KeyError:
            #     raise RuntimeError("Commit not found on that origin: {}".format(commit))
        else:
            try:
                ref = repo.remotes[REMOTE_NAME].refs.master
                ref_commit = ref.commit
                _dirname = "{:s}-m-{:s}".format(project_name, str(ref_commit)[:7])
            except (KeyError, AttributeError):
                raise RuntimeError("master ref not found on that origin.")
        if dirname is not None:
            # override dirname with one provided (like, "pr021")
            _dirname = "{:s}-{:s}".format(project_name, path_friendly(str(dirname)))
        linked_repo_path = path.join(location, _dirname)
        clone_dir = "{:s}-{:s}".format(project_name, str(ref_commit))
        new_repo_path = path.join(location, clone_dir)
        skip_symlink = False
        if path.exists(linked_repo_path):
            existing_repo = os.readlink(linked_repo_path)
            if not path.exists(existing_repo):
                # Old dangling symlink. Just kill it, and move on.
                try:
                    os.unlink(linked_repo_path)
                except Exception as e:
                    raise RuntimeError("Found a non-removable dangling symlink where we want to place a new "
                                       "directory link.")
            elif existing_repo == new_repo_path:
                # We already have this exact dirname linked to the correct repo!
                skip_symlink = True
            elif do_update:
                # First delete this symlink
                try:
                    os.unlink(linked_repo_path)
                except Exception as e:
                    if path.exists(linked_repo_path):
                        raise RuntimeError("Cannot update that dirname to new repo because the only link cannot "
                                           "be removed.\n"+str(e))
                    # old link is gone, lets continue
                # Terminate current version
                try:
                    resp = stop(existing_repo, wait=True)
                except Exception:
                    # Don't matter, just continue
                    pass
                # Remove the entire old directory tree
                try:
                    rmtree(existing_repo)
                except Exception:
                    pass
            else:
                raise RuntimeError("Oh no! That dir already exists pointing to another thing!")
        if not path.isdir(new_repo_path):
            cloned_repo = repo.clone(new_repo_path)
            cloned_repo.head.reference = cloned_repo.commit(ref_commit)
            # We're now in detached-head mode, this is what we want.
            # Now reset working tree to the specified commit
            cloned_repo.head.reset(index=True, working_tree=True)
        else:
            # clone of that project at that commit already exists!
            # just symlink it and call it done.
            pass
        if not skip_symlink:
            os.symlink(new_repo_path, linked_repo_path)
    finally:
        # Always remove the bare_location tree
        rmtree(bare_location)
    return linked_repo_path


class CleanEnv(object):

    params_to_clean = ["VIRTUAL_ENV", "PYTHON_HOME", "PS1", "PYTHONPATH", "LIBRARY_ROOTS"]
    params_to_save = ["PATH"]

    def __init__(self):
        self.old_vals = {}
        for p in self.params_to_clean:
            self.old_vals[p] = None
        for p in self.params_to_save:
            self.old_vals[p] = None

    def __enter__(self):
        for p in self.params_to_clean:
            self.old_vals[p] = environ.get(p, None)
        for p in self.params_to_save:
            self.old_vals[p] = environ.get(p, None)
        for p in self.params_to_clean:
            environ.unsetenv(p)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for p in self.params_to_clean:
            old_val = self.old_vals.get(p, None)
            if old_val is not None:
                environ.putenv(p, old_val)
        for p in self.params_to_save:
            old_val = self.old_vals.get(p, None)
            if old_val is not None:
                environ.putenv(p, old_val)


class InVenv(object):
    def __init__(self, venv_path=None):
        if venv_path is None:
            cwd = path.abspath(os.getcwd())
            venv_path = path.join(cwd, "venv")
        self.venv_path = venv_path
        self.old_path = None
        self.e = None
        self.p = None
        self.m = None

    def __enter__(self):
        self.old_path = old_path = environ.get("PATH", None)
        self.p = save_pkg_resources_state()
        pkgs = self.p.__enter__()
        self.m = save_modules()
        modules = self.m.__enter__()
        self.e = CleanEnv()
        self.e.__enter__()
        if old_path:
            first_colon = old_path.index(":")
            first_part = old_path[:first_colon]
            if first_part.endswith("venv/bin"):
                replacement_path = old_path[first_colon + 1 :]
                environ.putenv("PATH", replacement_path)
        if self.venv_path is False:
            # if isinstance(args, list):
            #     if args[0] == "python3":
            #         args[0] = "/usr/bin/python3"
            #     elif args[0] == "pip3":
            #         args[0] = "/usr/bin/pip3"
            #     elif args[0] == "python":
            #         args[0] = "/usr/bin/python"
            #     elif args[0] == "pip":
            #         args[0] = "/usr/bin/pip"
            # elif isinstance(args, str):
            #     if args.startswith("python3 "):
            #         args = args.replace("python3", "/usr/bin/python3", 1)
            #     elif args.startswith("python "):
            #         args = args.replace("python", "/usr/bin/python", 1)
            #     elif args.startswith("pip3 "):
            #         args = args.replace("pip3", "/usr/bin/pip3", 1)
            #     elif args.startswith("pip "):
            #         args = args.replace("pip", "/usr/bin/pip", 1)
            pass
        else:
            venv_parent = path.dirname(self.venv_path)
            activate_location = path.join(self.venv_path, "bin", "activate")

            cmd2 = ". {} && echo ~~MARKER~~ && set".format(activate_location)
            env = (
                subprocess.Popen(cmd2, shell=True, cwd=venv_parent, stdout=subprocess.PIPE)
                .stdout.read()
                .decode("utf-8")
                .splitlines()
            )
            marker = False
            new_envs = {}
            for e in env:
                if marker:
                    e = e.strip().split("=", 1)
                    if len(e) > 1:
                        name = str(e[0]).upper()
                        if name in ("IFS", "OPTIND"):
                            continue
                        else:
                            new_envs[name] = e[1].lstrip("'").rstrip("'")
                elif e.strip() == "~~MARKER~~":
                    marker = True
            environ.update(new_envs)
            # if isinstance(args, list):
            #     if args[0] == "python3":
            #         args[0] = path.join(venv_path, "bin", "python3")
            #     elif args[0] == "pip3":
            #         args[0] = path.join(venv_path, "bin", "pip3")
            #     elif args[0] == "python":
            #         args[0] = path.join(venv_path, "bin", "python")
            #     elif args[0] == "pip":
            #         args[0] = path.join(venv_path, "bin", "pip")
            # elif isinstance(args, str):
            #     if args.startswith("python3 "):
            #         args = args.replace("python3", path.join(venv_path, "bin", "python3"), 1)
            #     elif args.startswith("pip3 "):
            #         args = args.replace("pip3", path.join(venv_path, "bin", "pip3"), 1)
            #     elif args.startswith("python "):
            #         args = args.replace("python", path.join(venv_path, "bin", "python"), 1)
            #     elif args.startswith("pip "):
            #         args = args.replace("pip", path.join(venv_path, "bin", "pip"), 1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.e is not None:
            self.e.__exit__(exc_type, exc_val, exc_tb)
        if self.old_path is not None:
            environ.putenv("PATH", self.old_path)
        if self.m is not None:
            self.m.__exit__(exc_type, exc_val, exc_tb)
        if self.p is not None:
            self.p.__exit__(exc_type, exc_val, exc_tb)


class NoVenv(InVenv):
    def __init__(self):
        # Pass venv_path=False to indicate _no_ venv.
        super(NoVenv, self).__init__(venv_path=False)


def make_venv(parent_dir, venv_name="venv"):
    args = "/usr/bin/python3 -m venv --symlinks {}".format(venv_name)
    venv_path = path.join(parent_dir, venv_name)
    with NoVenv():
        resp = subprocess.run(args, cwd=parent_dir, shell=True)
    assert resp.returncode == 0
    assert path.isdir(venv_path)
    return venv_path


def init_pyproject_toml_project(file_path):
    if not path.isfile(file_path):
        return False, {}
    project_dir = path.dirname(file_path)
    venv_dir = make_venv(project_dir, venv_name=".venv")
    pip3_path = path.join(venv_dir, "bin", "pip3")
    poetry_path = path.join(venv_dir, "bin", "poetry")
    with InVenv(venv_dir):
        resp = subprocess.run([pip3_path, "install", "setuptools", "wheel"], cwd=project_dir, shell=False)
        resp = subprocess.run([pip3_path, "install", "poetry>=1.0.2"], cwd=project_dir, shell=False)
        # set poetry config
        # virtualenvs.in-project = true
        resp = subprocess.run(
            "{} config --local virtualenvs.in-project true".format(poetry_path), cwd=project_dir, shell=True
        )
        req_txt_file = path.join(project_dir, "tempreq.txt")
        resp = subprocess.run(
            "{} export -f requirements.txt --without-hashes -o {}".format(poetry_path, req_txt_file),
            cwd=project_dir,
            shell=True,
        )
    requirements = []
    if resp.returncode == 0:
        with open(req_txt_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        requirements.extend(lines)
        os.unlink(req_txt_file)
    return True, {"venv": venv_dir, "requirements": requirements}


def install_poetry_project(project_dir, venv_dir):
    poetry_path = path.join(venv_dir, "bin", "poetry")
    with InVenv(venv_dir):
        resp = subprocess.run("{} install".format(poetry_path), cwd=project_dir, shell=True)
    return resp

def init_setup_py_project(file_path):
    if not path.isfile(file_path):
        return False, {}
    project_dir = path.dirname(file_path)
    venv_dir = make_venv(project_dir, venv_name="dynvenv")
    import distutils.core
    with InVenv(venv_dir):
        setup = distutils.core.run_setup(file_path)
    requirements = setup.install_requires
    return True, {"venv": venv_dir, "requirements": requirements}


def install_setup_py_project(location, venv_dir):
    pip3 = path.join(venv_dir, "bin", "pip3")
    with InVenv(venv_dir):
        resp = subprocess.run([pip3, "install", "setuptools", "wheel"], cwd=location, shell=False)
        resp = subprocess.run("{} install .".format(pip3), cwd=location, shell=True)
    return resp


def init_requirements_txt_project(file_path):
    if not path.isfile(file_path):
        return False, {}
    project_dir = path.dirname(file_path)
    venv_dir = make_venv(project_dir, "dynvenv")
    requirements = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    requirements.extend(lines)
    return True, {"venv": venv_dir, "requirements": requirements}


def install_requirements_txt(project_dir, file_path, venv):
    pip3_path = path.join(venv, "bin", "pip3")
    with InVenv(venv):
        resp = subprocess.run([pip3_path, "install", "setuptools", "wheel"], cwd=project_dir, shell=False)
        resp = subprocess.run([pip3_path, "install", "-r", file_path], cwd=project_dir, shell=False)
    return resp


def install_gunicorn(venv):
    pip3_path = path.join(venv, "bin", "pip3")
    venv_parent = path.dirname(venv)
    with InVenv(venv):
        resp = subprocess.run([pip3_path, "install", "gunicorn>=20.0.1,<20.99"], cwd=venv_parent, shell=False)
    return resp


def load_gunicorn_conf(conf_file):
    g = {"__file__": conf_file}
    _locals = {}
    with NoVenv():
        try:
            with open(conf_file, "r") as f:
                exec(f.read(), g, _locals)
        except Exception:
            _locals = {}
    return _locals


def make_gunicorn_run(project_dir, venv, debug=True, workers=1, threads=4, target=None, **kwargs):
    venv_path = path.abspath(venv)
    if debug:
        log_level = "debug"
    else:
        log_level = "info"
    proj_name = path.basename(project_dir.rstrip("/"))
    run_file = path.join(project_dir, "run.sh")
    stop_file = path.join(project_dir, "stop.sh")
    conf_file = path.join(project_dir, "gunicorn.conf.py")
    extra = []
    if path.isfile(conf_file):
        gunicorn_conf = load_gunicorn_conf(conf_file)
        extra.append("-c ./gunicorn.conf.py")
    else:
        gunicorn_conf = {}
    if "app_module" in gunicorn_conf:
        target = gunicorn_conf["app_module"]
    if target is None:
        files = os.listdir(project_dir)
        if "app.py" in files:
            target = "app"
        elif "wsgi.py" in files:
            target = "wsgi"
        elif "application.py" in files:
            target = "application"
        else:
            target = "app"
    if "workers" in gunicorn_conf:
        workers = int(gunicorn_conf["workers"])
    if "threads" in gunicorn_conf:
        threads = int(gunicorn_conf["threads"])
    if "worker_class" in gunicorn_conf:
        extra.append("-k {}".format(str(gunicorn_conf["worker_class"])))
    elif kwargs.get("is_tornado_app", False):
        extra.append("-k tornado")
    elif kwargs.get("is_sanic_app", False):
        extra.append("-k sanic.worker.GunicornWorker")
    extra = " ".join(extra)
    run_template = """\
#!/bin/sh
. {venv_path:s}/bin/activate
exec {venv_path:s}/bin/gunicorn --log-level {log_level:s} -b unix:./gunicorn.sock --pid ./gunicorn.pid --workers {workers:d} --threads {threads:d} -n {proj_name:s} {extra:s} {target:s}
""".format(
        **locals()
    )
    stop_template = """\
#!/bin/sh
PIDFILE=./gunicorn.pid
SOCKFILE=./gunicorn.sock
if [ ! -f "$PIDFILE" ]; then
    exit 0
fi

read PID <$PIDFILE
kill -WINCH $PID
sleep 5
if [ -f "$PIDFILE" ]; then
    kill -TERM $PID
    sleep 10
fi

if [ -f "$PIDFILE" ]; then
    kill -9 $PID
    sleep 1
fi

rm -rf "$SOCKFILE"
rm -rf "$PIDFILE"
exit 0
""".format(
        **locals()
    )
    if not path.exists(run_file):
        with open(run_file, "w", encoding="latin-1") as f:
            f.write(run_template)
        os.chmod(run_file, 0o777)  # Executable for everyone.
    if not path.exists(stop_file):
        with open(stop_file, "w", encoding="latin-1") as f:
            f.write(stop_template)
        os.chmod(stop_file, 0o777)  # Executable for everyone
    return True


def launch(project_dir):
    with NoVenv():
        # cmdline = "/usr/bin/nuhup {} &".format(run_file)
        cmdline = "/usr/bin/nohup ./run.sh &"
        resp = subprocess.run(cmdline, cwd=project_dir, shell=True)
    return resp


def stop(project_dir, wait=False):
    if wait:
        cmdline = "./stop.sh"
    else:
        cmdline = "/usr/bin/nohup ./stop.sh &"
    with NoVenv():
        resp = subprocess.run(cmdline, cwd=project_dir, shell=True)
    return resp


def setup_python_project(location, execute=True):
    """
    We have a freshly cloned source codebase, now run it, but how?
    :param location:
    :type location: str
    :return: success or not
    :rtype: bool
    """
    # ACTION PLAN!
    # 1) Detect if there's pyproject.toml or requirements.txt or something else?
    # 2) Set up virtualenv for project to use
    # 3) Install requirements with either PIP or Poetry depending on project type
    # 4) Install gunicorn too (we need it to serve to a unix socket file)
    # 5) Detect if its a flask app or a sanic app (support for others to come)
    # 6) Detect where the app entrypoint is (app.py, app.wsgi, wsgi.py, source/app.py)?
    # 7) Create a `run_gunicorn.sh` file with shell script to run the app
    # 8) Execute it!

    # This routine will likely need to be modified and extended going forward as
    # we encounter more project types

    is_poetry_prj = False
    is_setup_py_prj = False
    is_bare_requirements = False
    found_parameters = {}
    dir_contents = os.listdir(location)
    if "pyproject.toml" in dir_contents:
        pyproject_location = path.join(location, "pyproject.toml")
        is_poetry_prj, params = init_pyproject_toml_project(pyproject_location)
        found_parameters.update(params)
    if not is_poetry_prj and "setup.py" in dir_contents:
        setup_py_location = path.join(location, "setup.py")
        is_setup_py_prj, params = init_setup_py_project(setup_py_location)
        found_parameters.update(params)
    if not is_poetry_prj and not is_setup_py_prj and "requirements.txt" in dir_contents:
        setup_py_location = path.join(location, "requirements.txt")
        is_bare_requirements, params = init_requirements_txt_project(setup_py_location)
        found_parameters.update(params)

    requirements = params.get("requirements", [])
    deploy_params = {
        "is_sanic_app": False,
        "is_flask_app": False,
        "is_tornado_app": False,
    }

    for r in requirements:
        r = str(r)
        if r.startswith("  ") or r.startswith("--"):
            continue
        r1 = str(r).lstrip(" -!").split("=", 1)[0].split(">", 1)[0].split("<", 1)[0].split("!", 1)[0].split(" ", 1)[0]
        if r1 == "sanic":
            deploy_params["is_sanic_app"] = True
            break
        elif r1 == "tornado":
            deploy_params["is_tornado_app"] = True
            break
        elif r1 == "flask":
            deploy_params["is_flask_app"] = True
            break

    if not any({deploy_params["is_flask_app"], deploy_params["is_sanic_app"], deploy_params["is_tornado_app"]}):
        pass  # assume its a generic wsgi-compatible app

    venv = params.get("venv", None)
    if is_poetry_prj and venv:
        resp = install_poetry_project(location, venv)
        print(resp)
    elif is_setup_py_prj and venv:
        resp = install_setup_py_project(location, venv)
    elif is_bare_requirements and venv:
        resp = install_requirements_txt(location, path.join(location, "requirements.txt"), venv)
    if venv:
        resp = install_gunicorn(venv)
    make_gunicorn_run(location, venv, **deploy_params)
    if execute:
        launch(location)


if __name__ == "__main__":
    here = path.abspath(os.getcwd())
    # v2 = make_venv(here, "dynvenv")
    # resp = run_in_venv(["python3", "--version"], venv_path=v2)
    # print(resp)
    setup_python_project(here)
