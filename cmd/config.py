import os
import sys

#hard coded configs for now. Can move to a config file if we want to.
MASTER_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = MASTER_DIR + "grading/"
SUBMISSION_DIR = MASTER_DIR + "submissions/"
CODE_REVIEW_DIR = GRADING_DIR + "codereview/"
REPO_DIR = _CODE_REVIEW_DIR + "repo/"
ASSIGN_DIR = MASTER_DIR + "lib/"
TEMP_DIR = MASTER_DIR + "tmp/robot-temp/tmp/"
PARAMS_FILE = GRADING_DIR + "params"

class ConfigException(Exception):
    pass

class Config:
    def __init__(self):
       pass 

    def get_imp_file(self, assignment):
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
        print("files is {}".format(files))
        if not files:
            raise ConfigException("Couldn't find {} in the params file".format(assignment))
        return files

