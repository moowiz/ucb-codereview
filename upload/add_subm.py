""" This script gets run whenever we get a new submission to upload.
    The login of the student is passed in as the second argument, and the assignment is passed as the first arguments.
    The steps to follow (should be fleshed out more) to add a submission are as follows:
    1. Unpack the submission into a temp directory.
    2. Move the file that has the student's code into their git repository.
    3. Add and commit their code.
    4. Upload their code.
"""
import argparse
import sys
import tempfile
from functools import reduce
import shutil
import os
import glob
import git
from config import *
import utils
from model import CodeReviewDatabase
model = CodeReviewDatabase()

class SubmissionException(Exception):
    pass

class UploadException(Exception):
    pass

def save_dir(func):
    def fun(*args, **kwds):
        original_dir = os.getcwd()
        try:
            func(*args, **kwds)
        except Exception as e:
            raise e
        finally:
            os.chdir(original_dir)
    return fun

def get_subm(data):
    """
    Gets the submission for the given login and assignment
    and moves the current directory to be in the temp directory they're stored in
    """
    print('Unpacking submission...')
    tempdir = config.TEMP_DIR
    files = glob.glob(config.TEMP_DIR + "*")
    for f in files:
        if os.path.isdir(f):
            shutil.rmtree(f)
        else:
            os.remove(f)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    os.chdir(tempdir)
    out, err = utils.run("get-subm " + data.assign + " " + data.login)
    print("Done unpacking.")
    timestamp = err[err.find(".") + 1: err.find("for")].strip()
    return tempdir + "/", timestamp #need the trailing slash for the copy command

def find_path(logins, data):
    """
    Finds the path to the given login's assignment git repository
    """
    logins.sort()
    logins = list(map(lambda x: x.strip(), logins))
    path = config.REPO_DIR + "".join(logins) + "/" + data.assign + "/"
    try:
        os.makedirs(path)
    except OSError:
        pass
    return path

def get_important_files(data):
    """
    Returns the files we want to copy.
    """
    assign_files = config.get_imp_files(data.assign)
    assign_files.extend(config.IMPORTANT_FILES)
    return assign_files

def get_sections():
    """
    Returns the sections for logins in a list
    """
    file = open(config.SECTIONS_FILE, 'r')
    text = file.read().split()
    rval = []
    for line in text:
        if len(line) == 3: #if they entered a 3 digit section code instead of a 2 digit
            line = line[1:]
        rval.append(line)
    file.close()
    return rval

def get_gmails():
    """
    Returns the gmail accounts (in a list) associated with these students for the code review system.
    """
    file = open(config.GMAILS_FILE, 'r')
    rval = file.read().split()
    file.close()
    return rval

PYTHON_BIN = "python2.7"
UPLOAD_SCRIPT = config.CODE_REVIEW_DIR + "61a-codereview/appengine/upload.py"
SERVER_NAME = "berkeley-61a.appspot.com"
ROBOT_EMAIL = "cs61a.robot@gmail.com"

@save_dir
def upload(path_to_repo, logins, data):
    """
    Calls the upload script with the needed arguments given the path to the repo and the
    gmail account of the student.
    """
    os.chdir(path_to_repo)
    if not data.gmails:
        data.gmails = get_gmails()
    if not data.gmails or len(data.gmails) == 0:
        raise UploadException("Student had no gmails. Not uploading.")
    issue_num = model.get_issue_number(logins, data.git_assign)
    sections = get_sections()
    reviewers = set()
    for section in sections:
        reviewers.update(set(model.get_reviewers(section)))
    gmails.extend(list(reviewers))
    hash_str = git.get_revision_hash(path_to_repo)
    #now we create arguments
    if not issue_num: #if this is the first time uploading...
        cmd = " ".join((PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
            "-t", data.git_assign, '-r', ",".join(data.gmails), '-e', ROBOT_EMAIL,
            '--rev', hash_str, '--private', "--send_mail"))
    else:
        cmd = " ".join((PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
            "-t", utils.get_timestamp_str(), '-e', ROBOT_EMAIL, '-i', str(issue_num),
            '--rev', hash_str, '--private', "--send_mail"))
    print("Uploading...")
    out, err = utils.run(cmd)
    if "Unhandled exception" in err:
        raise UploadException(str(err))
    print("Done uploading")
    line = ""
    for l in out.split('\n'):
        if l.startswith("Issue created"):
            line = l
            break
    if line:
        line = line[line.rfind('/') + 1:].strip()
        issue_num = int(line)
        print("New issue {}; adding to DB".format(issue_num))
        model.set_issue_numbers(logins, data.git_assign, issue_num)

def copy_important_files(data, start_dir, end_dir, template=False):
    files_to_copy = get_important_files(data.assign)
    if template:
        files_to_copy = list(filter(lambda x: x not in config.IMPORTANT_FILES, files_to_copy))
        if os.path.exists(end_dir):
            print("Removing files in {} because template.".format(end_dir))
            while os.path.exists(end_dir):
                files = os.listdir(end_dir)
                if not files:
                    break
                else:
                    f = files[0]
                if os.path.isdir(end_dir + f):
                    shutil.rmtree(end_dir + f)
                else:
                    os.remove(end_dir + f)
            if not os.path.exists(end_dir):
                os.mkdir(end_dir)
        for file in files_to_copy:
            dumb_template = open(end_dir + file, 'w')
            dumb_template.write("You were not given a template for this assignment.\nThis is just placehold text; nothing to freak out about :)\n")
            dumb_template.close()
    for filename in files_to_copy:
        if os.path.isdir(start_dir + filename):
            raise SubmissionException("ERROR. Turned in a directory that should be a file. Exiting...")
        shutil.copyfile(start_dir + filename, end_dir + filename)

@save_dir
def git_init(path):
    git.init(path=path)
    os.chdir(path)
    gitignore = open('.gitignore', 'w')
    gitignore.write("MY.*")
    gitignore.flush()
    gitignore.close()

def put_in_repo(data):
    """
    Puts the login's assignment into their repo
    """
    path_to_subm, timestamp = get_subm(data.login, data.assign)
    logins = list(map(lambda x: x.replace('\n', '').strip(), filter(lambda x: x, open(config.LOGINS_FILE, 'r').read().split(' '))))
    path_to_repo = find_path(logins, data.assign)
    issue_num = model.get_issue_number(logins, data.git_assign)
    if not issue_num:
        path_to_template = config.TEMPLATE_DIR
        if "hw" in data.assign:
            path_to_template += "hw/"
        else:
            path_to_template += "projects/"
        data.assign = utils.clean_assign(data.assign)
        if assign not in config.ASSIGN_TO_NAME_MAP:
            path_to_template += assign + "/"
        copy_important_files(assign, path_to_template, path_to_repo, template=True)
        git_init(path_to_repo)
        git.add(None, path=path_to_repo)
        git.commit("Initial commit", path=path_to_repo)
    else: #we want to check that we didnt mess up, and there is actually something here
        original_path = os.getcwd()
        os.chdir(path_to_repo)
        out, err = utils.run("git status")
        if "fatal: Not a git repository" in err:
            print("Issue number present, but no files in repository. Resetting issue number...")
            model.remove_issue_number(logins, data.git_assign, issue_num)
            os.chdir(original_path)
            return put_in_repo(login, assign)
        else: #we have a partner who submitted (I think)
            out, err = utils.run("git log --pretty=oneline --abbrev-commit")
            if "commit of code" not in out:
                raise SubmissionException("Found a git repository that hasn't been committed to yet. Ignoring...")
            last_line = out[:out.find("\n")]
            if last_line.find(":") != -1:
                com_time = last_line[last_line.find(":") + 1:]
                if com_time in timestamp:
                    raise SubmissionException("This timestamp ({}) has already been uploaded. Exiting...".format(timestamp))
        os.chdir(original_path)
    copy_important_files(assign, path_to_subm, path_to_repo)
    git.add(None, path=path_to_repo)
    git.commit("{} commit of code timestamp:{}".format(utils.get_timestamp_str(), timestamp), path=path_to_repo)
    shutil.rmtree(path_to_subm)
    files = glob.glob(path_to_repo + "*")
    for f in files:
        utils.chmod_own_grp(f)
        utils.chown_staff_master(f)
    return path_to_repo, logins

def add(data):
    utils.check_allowed_user()
    print("Adding {} for {}".format(data.assign, data.login))
    original_path = os.getcwd()
    try:
        path_to_repo, logins = put_in_repo(data)
        os.chdir(original_path) #need this because somehow we end up in a bad place here...
        upload(path_to_repo, logins, data)
    except IOError as e:
        if "No such file " in str(e):
            print("ERROR:{}. Ignoring...".format(str(e)), file=sys.stderr)
            return
        raise e
    except SubmissionException as e:
        print(str(e))
        return
    except UploadException as e:
        print("Error while uploading: {}".format(str(e)))
        return
    finally:
        os.chdir(original_path)

class Data:
    def __init__(self,login,assign,gmails=None):
        self.login = login
        self.assign = assign
        self.gmails = gmails
        if "revision" in self.assign:
            self.git_assign = self.assign[:self.assign.find("revision")]
        else:
            self.git_assign = assign

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds the given login's latest \
     submission for the given assignment to the code review system.")
    parser.add_argument('assign', type=str,
                        help='the assignment to look at')
    parser.add_argument('login', type=str,
                        help='the login to add')
    parser.add_argument('gmails', default=None,type=str,
                        nargs="*", help="Optional gmails to force the student to have.")
    args = parser.parse_args()
    data = Data(args.login, args.assign, args.gmails)
    add(args.login, args.assign, args.gmails)
