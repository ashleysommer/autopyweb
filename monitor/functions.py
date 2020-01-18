# -*- coding: utf-8 -*-
#
from os import path
import os
import git
from git import Repo

def debug_print(output, *args, **kwargs):
    print(output, *args, **kwargs)

def get_git_projects(location):
    location = path.abspath(location)
    contents = os.listdir(location)
    directories = [c for c in contents if path.isdir(c)]
    git_dirs = []
    for d in directories:
        d_contents = os.listdir(d)
        d_directories = [c for c in d_contents if path.isdir(c)]
        if ".git" in d_directories:
            git_dirs.append(d)
    debug_print("Found {} potential repo dirs. Now loading them in Repo classes.")
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

