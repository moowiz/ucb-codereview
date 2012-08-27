"""A basic wrapper for git
"""

import os
import utils

def add(files, path=None):
    """
    Adds the given files to the git repo at the given path
    Files is an iterable of string filenames.
    If files is None, then you add everything in the given directory instead.
    """
    if not files:
        files = ["-a"]
    if not path:
        path = os.getcwd()
    oldpath = os.getcwd()
    os.chdir(path)
    command = "git add " + " ".join(files)
    out = utils.run(command) 
    os.chdir(oldpath)

def commit(message, path=None):
    """
    Commits with the given message in the git repo in the given path. 
    Message is a string.
    """
    if not path:
        path = os.getcwd()
    oldpath = os.getcwd()
    os.chdir(path)
    command = "git commit " + message
    out = utils.run(command)
    os.chdir(oldpath)

def get_revision_hash(path_to_repo):
    oldpath = os.getcwd()
    os.chdir(path)
    command = "git log --pretty=format %H"
    out = utils.run(command)
    return out[-1]