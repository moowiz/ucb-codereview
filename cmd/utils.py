from subprocess import PIPE, Popen
from datetime import datetime
import os
import grp
import stat
import sys

def read_db_path():
    """
    Reads the DB path out of the config file.
    """
    return os.path.expanduser("~cs61a/grading/codereview/codereview_db.sqlite")
    # for local testing #return os.path.expanduser("../codereview_db.sqlite")

def run(cmd, content=""):
    """Run a shell command and pass content as stdin."""
    # print("running command {}".format(cmd))
    # print "cwd {}".format(os.getcwd())
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    content = bytes(content, "utf-8")
    out, err = proc.communicate(input=content)
    err = err.decode("utf-8")
    out = out.decode("utf-8")
    return out, err

def get_timestamp_str():
    now = datetime.now() #-2012-08-21-2-45
    return now.strftime("%Y-%m-%d-%H-%M")

def get_staff_gid():
    return grp.getgrnam("cs61a-staff")[2]

def get_master_user_id():
    return 20490

def chmod_own_grp(path):
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP) 

def chown_staff_master(path):
    os.chown(path, get_master_user_id(), get_staff_gid())

def clean_assign(assign):
    if len(assign) == 3: #wonderful hackage
        assign = assign[:2] + '0' + assign[-1]
    if len(assign) == 5:
        assign = assign[:4] + '0' + assign[-1]
    return assign