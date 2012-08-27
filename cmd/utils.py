from subprocess import PIPE, Popen
from datetime import datetime
import os
import grp

def read_db_path():
    """
    Reads the DB path out of the config file.
    """
    return os.path.expanduser("~cs61a/grading/codereview/codereview_db.sqlite")

def run(cmd, content=""):
    """Run a shell command and pass content as stdin."""
    # print "running command {}".format(cmd)
    # print "cwd {}".format(os.getcwd())
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE)
    out, err = proc.communicate(input=content)
    if err is not None:
        raise err
    return out

def get_timestamp_str():
    now = datetime.now() #-2012-08-21-2-45
    return now.strftime("%Y-%m-%d-%H-%M")

def get_staff_gid():
    return grp.getgrname("cs61a-staff")[2]

def get_master_user_id():
    return 20490

def chmod_own_grp(path):
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP) 

def chown_staff_master(path):
    os.chown(path, get_master_user_id(), get_staff_gid())