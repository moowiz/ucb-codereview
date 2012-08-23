"""A basic wrapper for git
"""

import os

def add(files, path=None):
    """
    Adds the given files to the git repo at the given path
    Files is an iterable of string filenames.
    If files is None, then you add everything in the given directory instead.
    """
    if not files:
        files = ["*"]
    if not path:
        path = os.getcwd()
    oldpath = os.getcwd()
    os.chdir(path)
    command = "git add "
    for file in files:
        command += file + " "
    res = os.system(command)
    if res:
        print("uh oh!")
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
    res = os.system(command)
    if res:
        print("uh oh!")
    os.chdir(oldpath)