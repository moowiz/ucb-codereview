import os
import sys

#hard coded configs for now. Can move to a config file if we want to.
_MASTER_DIR = os.path.expanduser('~cs61a/')
_GRADING_DIR = _MASTER_DIR + "grading/"
_SUBMISSION_DIR = _MASTER_DIR + "submissions/"
_CODE_REVIEW_DIR = _GRADING_DIR + "codereview/"
_REPO_DIR = _CODE_REVIEW_DIR + "repo/"
_ASSIGN_DIR = _MASTER_DIR + "lib/"
_TEMP_DIR = _MASTER_DIR + "tmp/robot-temp/tmp/"
_PARAMS_FILE = _GRADING_DIR + "params"

class ConfigException(Exception):
    pass

def get_imp_file(assignment):
    if len(assignment) == 4 and assignment[2] != "1":
        assignment = assignment[:2] + assignment[-1]
    if len(assignment) == 6 and assignment[4] != "1":
        assignment = assignment[:4] + assignment[-1]
    f = open(_PARAMS_FILE, 'r')
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
    print("files is {}".format(files))
    if not files:
        raise ConfigException("Couldn't find {} in the params file".format(assignment))
    return files

