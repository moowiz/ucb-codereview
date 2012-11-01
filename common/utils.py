from subprocess import PIPE, Popen
from datetime import datetime
import os
import grp
import stat
import sys
import getpass
from config import *
import pwd
import re

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
    return grp.getgrnam(config.STAFF_GROUP)[2]

def getuser():
    return getpass.getuser()

_REGEX_USER = config.CLASS_NAME + "-t[a-z]"

def check_allowed_user():
    if not re.match(_REGEX_USER, getuser()) and not getuser() == config.CLASS_NAME:
        print("ERROR: Only TA accounts are allowed to run this script.", file=sys.stderr)
        sys.exit(1)

def get_master_user_id():
    return pwd.getpwnam(config.CLASS_NAME)[2]

def chmod_own_grp(path):
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP)

def chmod_own_grp_other_read(path):
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH)

def chown_staff_master(path):
    os.chown(path, get_master_user_id(), get_staff_gid())

def clean_assign(assign):
    if 'hw' in assign and (len(assign) == 3 or not assign[3].isdigit()): #wonderful hackage
        assign = assign[:2] + '0' + assign[3:]
    elif 'proj' in assign and (len(assign) < 5 or not assign[5].isdigit()):
        assign = assign[:4] + '0' + assign[4:]
    return assign
