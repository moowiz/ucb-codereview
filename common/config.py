import os
import sys

#hard coded configs for now. Can move to a config file if we want to.
class Config_Class:
    def __init__(self):
        config = {
            "CLASS_NAME" : None, # 'cs61a'
            "MASTER_DIR" : None, # os.path.expanduser(CLASS_NAME)
            "STAFF_GROUP" : None, # 'cs61a-staff'
            "GRADING_DIR" : None, # MASTER_DIR + "grading/"
            "SUBMISSION_DIR" : None, # MASTER_DIR + "submissions/"
            "CODE_REVIEW_DIR" : None, # GRADING_DIR + "codereview/"
            "REPO_DIR" : None, # CODE_REVIEW_DIR + "repo/"
            "ASSIGN_DIR" : None, # MASTER_DIR + "lib/"
            "TEMP_DIR" : None, # MASTER_DIR + "tmp/robot-temp/tmp/"
            "TEMPLATE_DIR" : None, # MASTER_DIR + "public_html/fa12/"
            "PARAMS_FILE" : None, # GRADING_DIR + "params"
            "GMAILS_FILE" : None, # "MY.GMAILS"
            "SECTIONS_FILE" : None, # "MY.SECTIONS"
            "LOGINS_FILE" : None, # "MY.PARTNERS"
            "IMPORTANT_FILES" : None, # (GMAILS_FILE, SECTIONS_FILE, LOGINS_FILE)
            "ASSIGN_TO_NAME_MAP" : {
                    "proj1" : "hog",
                    "proj3" : "ants"
                },
            "DB_PATH" : None #CODE_REVIEW_DIR + "codereview_db.sqlite"
        }
        for k, v in config.items():
            self.__dict__[k] = v

    def generate(self):
        self.GRADING_DIR = self.MASTER_DIR + "grading/"
        self.SUBMISSION_DIR = self.MASTER_DIR + "submissions/"
        self.CODE_REVIEW_DIR = self.GRADING_DIR + "codereview/"
        self.REPO_DIR = self.CODE_REVIEW_DIR + "repo/"
        self.ASSIGN_DIR = self.MASTER_DIR + "lib/"
        self.TEMP_DIR = self.MASTER_DIR + "tmp/robot-temp/tmp/"
        self.TEMPLATE_DIR = self.MASTER_DIR + "public_html/fa12/"
        self.PARAMS_FILE = self.GRADING_DIR + "params"
        self.GMAILS_FILE = "MY.GMAILS"
        self.SECTIONS_FILE = "MY.SECTIONS"
        self.LOGINS_FILE = "MY.PARTNERS"
        self.IMPORTANT_FILES = (self.GMAILS_FILE, self.SECTIONS_FILE, self.LOGINS_FILE)
        self.DB_PATH = self.CODE_REVIEW_DIR + "codereview_db.sqlite"

config = Config_Class()

class ConfigException(Exception):
    pass

def get_imp_files(assignment):
    if len(assignment) == 4 and assignment[2] != "1":
        assignment = assignment[:2] + assignment[-1]
    if len(assignment) == 6 and assignment[4] != "1":
        assignment = assignment[:4] + assignment[-1]
    f = open(config.PARAMS_FILE, 'r')
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

def load_params():
    f = open(config.PARAMS_FILE, 'r')
    lines = f.read().split("\n")
    f.close()
    lines = list(filter(lambda s: 'set' not in s.split(" ")[0], lines))
    for line in lines:
        print("line is " + line)
        if "STAFF_GROUP" in line:
            config.STAFF_GROUP = line.split(" ")[2][1:-1]
    if config.STAFF_GROUP == None:
        raise ConfigException("Couldn't find the staff group in the params file")


def init_config():
    #the master directory for this user is stored in the environment!
    if not "MASTERDIR" in os.environ:
        print("ERROR: \"MASTERDIR\" is not set in the current environment", file=sys.stderr)
        sys.exit(1)
    else:
        config.MASTER_DIR = os.environ["MASTERDIR"]
        if config.MASTER_DIR[-1] != "/":
            config.MASTER_DIR += "/"
        config.CLASS_NAME = os.environ["MASTER"]
        config.generate()
        load_params()

init_config()
