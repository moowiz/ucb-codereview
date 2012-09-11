import os
import sys

#hard coded configs for now. Can move to a config file if we want to.
CLASS_NAME = 'cs61a'
MASTER_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = MASTER_DIR + "grading/"
SUBMISSION_DIR = MASTER_DIR + "submissions/"
CODE_REVIEW_DIR = GRADING_DIR + "codereview/"
REPO_DIR = CODE_REVIEW_DIR + "repo/"
ASSIGN_DIR = MASTER_DIR + "lib/"
TEMP_DIR = MASTER_DIR + "tmp/robot-temp/tmp/"
PARAMS_FILE = GRADING_DIR + "params"
GMAILS_FILE = "MY.GMAILS"
SECTIONS_FILE = "MY.SECTIONS"
LOGINS_FILE = "MY.PARTNERS"
IMPORTANT_FILES = (GMAILS_FILE, SECTIONS_FILE, LOGINS_FILE)

class ConfigException(Exception):
    pass

def get_imp_files(assignment):
    if len(assignment) == 4 and assignment[2] != "1":
        assignment = assignment[:2] + assignment[-1]
    if len(assignment) == 6 and assignment[4] != "1":
        assignment = assignment[:4] + assignment[-1]
    f = open(PARAMS_FILE, 'r')
    lines = f.read().split("\n")
    f.close()
    ind = 0
    for i, line in enumerate(lines):
        if line.startswith("assign"):
            ind = i
            break
    lines = lines[ind:]
    #skip the first one, because lines begins with assign
    spl = "\n".join(lines).split("assign")[1:] 
    files = []
    for assign_spl in spl:
        split = list(filter(lambda x: x and x != "\\\n" and x != "\n", assign_spl.split(" ")))
        assign = split[0]
        if not assign == assignment:
            continue
        split.pop(0)
        commands, args = split[::2], split[1::2]
        commands = list(map(lambda x: x if x == "-req" else None, commands))
        for i, command in enumerate(commands):
            if command:
                files.append(args[i][1:-1])
        break
    files = list(map(lambda x: x.replace("\n\n", '').replace("\n", "").replace("'", ""), files))
    if not files:
        raise ConfigException("Couldn't find {} in the params file".format(assignment))
    return files

def init_config():
    #the master directory for this user is stored in the environment!
    if not "MASTERDIR" in os.environ:
        print("ERROR: \"MASTERDIR\" is not set in the current environment", file=sys.stderr)
        sys.exit(1)
    else:
        MASTER_DIR = os.environ["MASTERDIR"]
    #to do in the future; read the params file and parse lots of fun info and/or our own config file

init_config()
