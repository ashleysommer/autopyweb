# -*- coding: utf-8 -*-
#
from os import path, environ
import subprocess
import os
import git
from git import Repo, Head, Tag
from shutil import rmtree
import time
from venv import EnvBuilder

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

def add_git_project(location, origin_url, tag=None, branch=None, commit=None, dirname=None, **kwargs):
    project_name = path_friendly(guess_project_name(origin_url))
    location = path.abspath(location)
    t = str(int(time.time()))
    bare_location = path.join(location, 'bare-{}-{}'.format(project_name, t))
    if path.isdir(bare_location):
        rmtree(bare_location)
    repo = Repo.init(bare_location, bare=True)
    try:
        REMOTE_NAME='origin'
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
                _dirname = "tag-{:s}-{:s}".format(path_friendly(tag), str(ref_commit)[:7])
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
                _dirname = "br-{:s}-{:s}".format(path_friendly(branch), str(ref_commit)[:7])
            except KeyError:
                raise RuntimeError("Branch not found on that origin: {}".format(branch))
        elif commit is not None:
            raise NotImplementedError("Cannot fetch remote reference from just a commit id.")
            # try:
            #     ref = repo.remotes[REMOTE_NAME].refs[commit]
            #     _dirname = "sha-{:s}".format(ref.commit)
            # except KeyError:
            #     raise RuntimeError("Commit not found on that origin: {}".format(commit))
        else:
            try:
                ref = repo.remotes[REMOTE_NAME].refs.master
                ref_commit = ref.commit
                _dirname = 'm-{:s}'.format(str(ref_commit)[:7])
            except (KeyError, AttributeError):
                raise RuntimeError("master ref not found on that origin.")
        if dirname is not None:
            # override dirname with one provided (like, "pr021")
            _dirname = path_friendly(str(dirname))
        linked_repo_path = path.join(location, _dirname)
        clone_dir = "{}-{:s}".format(project_name, str(ref_commit))
        new_repo_path = path.join(location, clone_dir)
        if path.exists(linked_repo_path):
            existing_link = os.readlink(linked_repo_path)
            if existing_link == clone_dir:
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
        os.symlink(new_repo_path, linked_repo_path)
    finally:
        # Always remove the bare_location tree
        rmtree(bare_location)
    return linked_repo_path

def run_in_venv(args, cwd=None, shell=False, venv_path=None):
    if cwd is None:
        cwd = path.abspath(os.getcwd())
    if venv_path is None:
        venv_path = path.join(cwd, "venv")
    old_virtual_env = environ.get("VIRTUAL_ENV", None)
    old_path = environ.get("PATH", None)
    old_python_home = environ.get("PYTHON_HOME", None)
    old_ps1 = environ.get("PS1", None)
    old_pythonpath = environ.get("PYTHONPATH", None)
    old_library_roots = environ.get("LIBRARY_ROOTS", None)
    environ.unsetenv("VIRTUAL_ENV")
    environ.unsetenv("PYTHON_HOME")
    environ.unsetenv("PS1")
    environ.unsetenv("PYTHONPATH")
    environ.unsetenv("LIBRARY_ROOTS")
    if old_path:
        first_colon = old_path.index(":")
        first_part = old_path[:first_colon]
        if first_part.endswith("venv/bin"):
            replacement_path = old_path[first_colon+1:]
            environ.putenv("PATH", replacement_path)
    if venv_path is False:
        if isinstance(args, list):
            if args[0] == "python3":
                args[0] = "/usr/bin/python3"
            elif args[0] == "pip3":
                args[0] = "/usr/bin/pip3"
            elif args[0] == "python":
                args[0] = "/usr/bin/python"
            elif args[0] == "pip":
                args[0] = "/usr/bin/pip"
        elif isinstance(args, str):
            if args.startswith("python3 "):
                args = args.replace("python3", "/usr/bin/python3", 1)
            elif args.startswith("python "):
                args = args.replace("python", "/usr/bin/python", 1)
            elif args.startswith("pip3 "):
                args = args.replace("pip3", "/usr/bin/pip3", 1)
            elif args.startswith("pip "):
                args = args.replace("pip", "/usr/bin/pip", 1)
    else:
        activate_location = path.join(venv_path, "bin", "activate")
        cmd2 = ". {} && echo ~~MARKER~~ && set".format(activate_location)
        env = (subprocess.Popen(cmd2, shell=True, cwd=cwd, stdout=subprocess.PIPE)
               .stdout.read().decode('utf-8').splitlines())
        marker = False
        new_envs = {}
        for e in env:
            if marker:
                e = e.strip().split('=', 1)
                if len(e) > 1:
                    name = str(e[0]).upper()
                    if name in ("IFS", "OPTIND"):
                        continue
                    else:
                        new_envs[name] = e[1].lstrip("'").rstrip("'")
            elif e.strip() == "~~MARKER~~":
                marker = True
        environ.update(new_envs)
        if isinstance(args, list):
            if args[0] == "python3":
                args[0] = path.join(venv_path, "bin", "python3")
            elif args[0] == "pip3":
                args[0] = path.join(venv_path, "bin", "pip3")
            elif args[0] == "python":
                args[0] = path.join(venv_path, "bin", "python")
            elif args[0] == "pip":
                args[0] = path.join(venv_path, "bin", "pip")
        elif isinstance(args, str):
            if args.startswith("python3 "):
                args = args.replace("python3", path.join(venv_path, "bin", "python3"), 1)
            elif args.startswith("pip3 "):
                args = args.replace("pip3", path.join(venv_path, "bin", "pip3"), 1)
            elif args.startswith("python "):
                args = args.replace("python", path.join(venv_path, "bin", "python"), 1)
            elif args.startswith("pip "):
                args = args.replace("pip", path.join(venv_path, "bin", "pip"), 1)

    resp = subprocess.run(args, cwd=cwd, shell=shell, stdout=subprocess.PIPE)
    if old_library_roots is not None:
        environ.putenv("LIBRARY_ROOTS", old_library_roots)
    else:
        environ.unsetenv("LIBRARY_ROOTS")
    if old_pythonpath is not None:
        environ.putenv("PYTHONPATH", old_pythonpath)
    else:
        environ.unsetenv("PYTHONPATH")
    if old_virtual_env is not None:
        environ.putenv("VIRTUAL_ENV", old_virtual_env)
    else:
        environ.unsetenv("VIRTUAL_ENV")

    if old_path is not None:
        environ.putenv("PATH", old_path)
    else:
        environ.unsetenv("PATH")
    if old_python_home is not None:
        environ.putenv("PYTHON_HOME", old_python_home)
    else:
        environ.unsetenv("PYTHON_HOME")
    if old_ps1 is not None:
        environ.putenv("PS1", old_ps1)
    else:
        environ.unsetenv("PS1")
    return resp

def run_without_venv(args, cwd=None, shell=False):
    return run_in_venv(args, cwd=cwd, shell=shell, venv_path=False)

def make_venv(parent_dir, venv_name="venv"):
    args = "python3 -m venv --symlinks {}".format(venv_name)
    venv_path = path.join(parent_dir, venv_name)
    resp = run_without_venv(args, parent_dir, shell=True)
    assert resp.returncode == 0
    assert path.isdir(venv_path)
    return venv_path

def process_pyproject_toml(file_path):
    if not path.isfile(file_path):
        return False, {}
    project_dir = path.dirname(file_path)
    venv_path = make_venv(project_dir, "testvenv")
    resp = run_in_venv(["pip3", "install", "poetry>=1.0.2"], cwd=project_dir, shell=False, venv_path=venv_path)
    poetry_path = path.join(venv_path, "bin", "poetry")
    # set poetry config
    #virtualenvs.in-project = true
    resp = run_in_venv("{} config --local virtualenvs.in-project true".format(poetry_path), cwd=project_dir, shell=True, venv_path=venv_path)
    req_txt_file = path.join(project_dir, "tempreq.txt")
    resp = run_in_venv("{} export -f requirements.txt -o {}".format(poetry_path, req_txt_file), cwd=project_dir, shell=True, venv_path=venv_path)
    requirements = []
    if resp.returncode == 0:
        with open(req_txt_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        requirements.extend(lines)

    return True, {"venv": venv_path, "requirements": requirements}

def install_poetry_project(project_dir, venv):
    poetry_path = path.join(venv, "bin", "poetry")
    resp = run_in_venv("{} install".format(poetry_path), cwd=project_dir, shell=True, venv_path=venv)
    return resp


def process_setup_py(file_path):
    if not path.isfile(file_path):
        return False, {}
    import distutils.core
    setup = distutils.core.run_setup(file_path)
    print(setup.install_requires)

def setup_python_project(location):
    """
    We have a freshly cloned source codebase, now run it, but how?
    :param location:
    :type location: str
    :return: success or not
    :rtype: bool
    """
    # ACTION PLAN!
    # 1) Detect if there's requirements.txt or pyproject.toml or something else?
    # 2) Set up virtualenv for project to use
    # 3) Install requirements with either PIP or Poetry depending on project type
    # 4) Install gunicorn too (we need it to serve to a unix socket file)
    # 5) Detect if its a flask app or a sanic app (support for others to come)
    # 6) Detect where the app entrypoint is (app.py, app.wsgi, wsgi.py, source/app.py)?
    # 7) Create a `run_gunicorn.sh` file with shell script to run the app

    # This routine will likely need to be modified and extended going forward as
    # we encounter more project types

    is_poetry_prj = False
    is_setup_py_prj = False
    is_bare_requirements = False
    dir_contents = os.listdir(location)
    if "pyproject.toml" in dir_contents:
        pyproject_location = path.join(location, "pyproject.toml")
        is_poetry_prj, params = process_pyproject_toml(pyproject_location)
    if not is_poetry_prj and "setup.py" in dir_contents:
        setup_py_location = path.join(location, "setup.py")
        is_setup_py_prj, params = process_setup_py(setup_py_location)
    requirements = params.get("requirements", [])
    venv = params.get("venv", None)
    if is_poetry_prj and venv:
        resp = install_poetry_project(location, venv)
        print(resp)

if __name__ == "__main__":
    here = path.abspath(os.getcwd())
    # v2 = make_venv(here, "testvenv")
    # resp = run_in_venv(["python3", "--version"], venv_path=v2)
    # print(resp)
    setup_python_project(here)
