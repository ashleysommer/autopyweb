# -*- coding: utf-8 -*-
#
from os import path
import os
import git
from git import Repo, Head, Tag
from shutil import rmtree
import time

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
            # clone of that project with that commit already exists!
            # just symlink it and call it done.
            pass
        os.symlink(new_repo_path, linked_repo_path)
    finally:
        # Always remove the bare_location tree
        rmtree(bare_location)
    return linked_repo_path

