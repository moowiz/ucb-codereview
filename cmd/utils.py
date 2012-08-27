from subprocess import PIPE, Popen
from datetime import datetime
import os

def read_db_path():
    """
    Reads the DB path out of the config file.
    """
    return os.path.expanduser("~cs61a/grading/codereview/codereview_db.sqlite")

def run(cmd, content=""):
    """Run a shell command and pass content as stdin."""
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE)
    out, err = proc.communicate(input=content)
    if err is not None:
        raise err
    return out

def get_timestamp_str():
    now = datetime.now() #-2012-08-21-2-45
    return now.strftime("%Y-%m-%d-%H-%M")