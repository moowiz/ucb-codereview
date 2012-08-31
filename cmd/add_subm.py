""" This script gets run whenever we get a new submission to upload.
    The login of the student is passed in as the first argument.
    The steps to follow (should be fleshed out more) to add a submission are as follows:
    1. Unpack the submission into a temp directory.
    2. Move the file that has the student's code into their git repository.
    3. Add and commit their code.
    4. Upload their code.
"""
import argparse
import sys
import tempfile
import shutil
import utils
import os
import glob
import git
import submit
from functools import reduce

from model import CodeReviewDatabase
model = CodeReviewDatabase(utils.read_db_path())

class SubmissionException(Exception):
    pass

HOME_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = HOME_DIR + "grading/"
SUBMISSION_DIR = HOME_DIR + "submissions/"
CODE_REVIEW_DIR = GRADING_DIR + "codereview/"
REPO_DIR = CODE_REVIEW_DIR + "repo/"
ASSIGN_DIR = HOME_DIR + "lib/"
TEMP_DIR = HOME_DIR + "tmp/robot-temp/tmp/"

def get_subm(login, assign):
    """
    Gets the submission for the given login and assignment
    and moves the current directory to be in the temp directory they're stored in
    """
    print('Unpacking submission...')
    tempdir = TEMP_DIR
    files = glob.glob(TEMP_DIR + "*")
    for f in files:
        if os.path.isdir(f):
            shutil.rmtree(f)
        else:
            os.remove(f)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    os.chdir(tempdir)
    out, err = utils.run("get-subm " + assign + " " + login)
    # if err:
        # print("ERROR: {}".format(err))
    # print 'hmmm'
    # print 'logins {} assign {}'.format(logins, assign)
    # print("out is {}".format(out))
    print("Done unpacking.")
    return tempdir + "/" #need the trailing slash for the copy command

def find_path(logins, assign):
    """
    Finds the path to the given login's assignment git repository
    """
    path = REPO_DIR + "".join(logins) + "/" + assign + "/"
    try:
        os.makedirs(path)
    except OSError:
        pass
    return path

def get_important_files(assign):
    """
    Returns the files we want to copy.
    Do we need this function, or should we copy everything?
    Would involve either some looking at the params file, or looking at the DB
    """
    assign_files = model.get_important_file(assign)
    assign_files.extend(submit.important_files)
    return assign_files

def get_sections(logins):
    """
    Returns the sections for logins in a list
    """
    return open(submit.SECTIONS_FILE, 'r').read().split()

def get_gmails(logins):
    """
    Returns the gmail accounts (in a list) associated with these students for the code review system.
    Not sure how to do this yet; we'll decide something in the first staff meeting
    """
    return open(submit.GMAILS_FILE, 'r').read().split()

PYTHON_BIN = "python2.7"
UPLOAD_SCRIPT = CODE_REVIEW_DIR + "61a-codereview/appengine/upload.py"
SERVER_NAME = "berkeley-61a.appspot.com"
ROBOT_EMAIL = "cs61a.robot@gmail.com"

def get_robot_pass():
    """
    We shouldn't ever call this....
    """
    return "reviewdatcode"

def upload(path_to_repo, logins, assign):
    """
    ~cs61a/code_review/repo/login/assign/
    Calls the upload script with the needed arguments given the path to the repo and the
    gmail account of the student.
    Arguments we care about:
    -r reviewers
    --cc people to cc
    --private makes the issue private 
    --send_mail sends an email to the reviewers (might want)
    --send_patch sends an email but with the diff attached, possible thing to do
    new version of the same issue
    each issue is the same project
    These args are documented in upload.py starting on line 490.
    This method also needs to deal with assigning the correct people to this, which means
    it has to probably get info from somewhere about the roster. 
    """
    original_path = os.getcwd()
    try:
        os.chdir(path_to_repo)
        gmails = get_gmails(logins)
        issue_num = model.get_issue_number(logins, assign)
        def mextend(a, b):
            a.extend(b)
            return a
        sections = get_sections(logins)
        reviewers = set()
        for section in sections:
            reviewers.update(set(model.get_reviewers(section)))
        gmails.extend(list(reviewers))
        hash_str = git.get_revision_hash(path_to_repo)
        if not issue_num:
            cmd = " ".join((PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
                "-t", assign, '-r', ",".join(gmails), '-e', ROBOT_EMAIL,
                '--rev', hash_str, '--private'))
        else:
            cmd = " ".join((PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
                "-t", utils.get_timestamp_str(), '-e', ROBOT_EMAIL, '-i', str(issue_num),
                '--rev', hash_str, '--private'))
        print("Uploading...")
        out, err = utils.run(cmd)
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
            model.set_issue_number(logins, assign, issue_num)  
    except Exception as e:
        raise e 
    finally:
        os.chdir(original_path)

def copy_important_files(assign, start_dir, end_dir, template=False):
    original_path = os.getcwd()
    files_to_copy = get_important_files(assign)
    if template:
        files_to_copy = list(filter(lambda x: x not in submit.important_files, files_to_copy))
        for file in files_to_copy:
            dumb_template = open(path_to_template + file, 'w')
            dumb_template.write("You were not given a template for this assignment.\n")
            dumb_template.flush()
            dumb_template.close()
        if os.path.exists(end_dir):
            print("Removing files in {} because template.".format(end_dir))
            shutil.rmtree(end_dir)
    for filename in files_to_copy:
        if os.path.isdir(start_dir+filename):
            raise SubmissionException("ERROR. Turned in a directory that should be a file. Exiting...")
        shutil.copy(start_dir + filename, end_dir + filename)

def git_init(path):
    git.init(path=path)
    original_path = os.getcwd()
    os.chdir(path)
    gitignore = open('.gitignore', 'w')
    gitignore.write("MY.*")
    gitignore.flush()
    gitignore.close()

def put_in_repo(login, assign):
    """
    Puts the login's assignment into their repo
    """
    path_to_subm = get_subm(login, assign)
    logins = open(submit.LOGINS_FILE, 'r').read().split('\n')
    path_to_repo = find_path(logins, assign)
    issue_num = model.get_issue_number(logins, assign)
    if not issue_num:
        path_to_template = ASSIGN_DIR
        if "hw" in assign:
            path_to_template += "hw/"
        else:
            path_to_template += "proj/"
        assign = utils.clean_assign(assign)
        path_to_template += assign + "/"
        git_init(path_to_repo)
        copy_important_files(assign, path_to_template, path_to_repo, template=True)
        git.add(None, path=path_to_repo)
        git.commit("Initial commit", path=path_to_repo)
    else: #we want to check that we didnt mess up, and there is actually something here
        out, err = utils.run("git status")
        if "fatal: Not a git repository" in err:
            print("Issue number present, but no files in repository. Resetting issue number...")
            model.remove_issue_number(logins, assign, issue_num)
            return put_in_repo(login, assign)
    copy_important_files(assign, path_to_subm, path_to_repo)
    git.add(None, path=path_to_repo)
    git.commit("{} commit of code".format(utils.get_timestamp_str()), path=path_to_repo)
    shutil.rmtree(path_to_subm)
    files = glob.glob(path_to_repo + "*")
    for f in files:
        utils.chmod_own_grp(f)
        utils.chown_staff_master(f)
    return path_to_repo, logins

def add(login, assign):
    print("Adding {} for {}".format(assign, login))
    utils.check_master_user()
    original_path = os.getcwd()
    try:
        path_to_repo, logins = put_in_repo(login, assign)
        os.chdir(original_path) #need this because somehow we end up in a bad place now...
        upload(path_to_repo, logins, assign)
    except IOError as e:
        if "No such file " in str(e):
            print("ERROR: Couldn't find a file {}. Ignoring login...".format(str(e)), file=sys.stderr)
            os.chdir(original_path)
            return
        raise e
    except SubmissionException as e:
        print(str(e))
        os.chdir(original_path)
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds the given login's latest \
     submission for the given assignment to the code review system.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to look at')
    parser.add_argument('login', type=str,
                        help='the login to add')
    args = parser.parse_args()
    add(args.login, args.assign)
