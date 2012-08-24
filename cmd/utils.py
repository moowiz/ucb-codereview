from subprocess import PIPE, Popen

def read_db_path():
    """
    Reads the DB path out of the config file.
    """
    return "codereview_db.sqlite"

def run(cmd, content=""):
    """Run a shell command and pass content as stdin."""
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE)
    out, err = proc.communicate(input=content)
    if err is not None:
        raise err
    return out