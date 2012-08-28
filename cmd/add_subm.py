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
import new_submit

from model import CodeReviewDatabase
model = CodeReviewDatabase(utils.read_db_path())

HOME_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = HOME_DIR + "grading/"
SUBMISSION_DIR = HOME_DIR + "submissions/"
CODE_REVIEW_DIR = GRADING_DIR + "codereview/"
REPO_DIR = CODE_REVIEW_DIR + "repo/"
ASSIGN_DIR = HOME_DIR + "lib/"
TEMP_DIR = HOME_DIR + "tmp/robot-tmp/"

def get_subm(login, assign):
    """
    Gets the submission for the given login and assignment
    and moves the current directory to be in the temp directory they're stored in
    """
    tempdir = TEMP_DIR
    files = glob.glob(TEMP_DIR + "*")
    for f in files:
        os.remove(f)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    os.chdir(tempdir)
    out = utils.run("get-subm " + assign + " " + login)
    # print 'hmmm'
    # print 'logins {} assign {}'.format(logins, assign)
    # print("out is {}".format(out))
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
    assign_files.extend(new_submit.important_files)
    return assign_files

def get_sections(logins):
    """
    Returns the sections for logins in a list
    """
    return open(new_submit.SECTIONS_FILE, 'r').read().split()

def get_gmails(logins):
    """
    Returns the gmail accounts (in a list) associated with these students for the code review system.
    Not sure how to do this yet; we'll decide something in the first staff meeting
    """
    return open(new_submit.GMAILS_FILE, 'r').read().split()

PYTHON_BIN = "python2.7"
UPLOAD_SCRIPT = CODE_REVIEW_DIR + "61a-codereview/appengine/upload.py"
SERVER_NAME = "berkeley-61a.appspot.com"
ROBOT_EMAIL = "cs61a.robot@gmail.com"

def get_robot_pass():
    return "reviewdatcode"

def upload(path_to_repo, gmails, logins, assign):
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
        issue_num = model.get_issue_number(logins, assign)
        def mextend(a, b):
            a.extend(b)
            return a
        staff_gmails = reduce(mextend, map(lambda x: model.get_reviewers(x), get_sections(logins)), [])
        gmails.extend(staff_gmails)
        content = ""
        hash_str = git.get_revision_hash(path_to_repo)
        if not issue_num:
            cmd = " ".join((PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
                "-t", assign, '-r', ",".join(gmails), '-e', ROBOT_EMAIL,
                '--rev', hash_str, '--private'))
            content = get_robot_pass()
        else:
            cmd = " ".join((PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
                "-t", utils.get_timestamp_str(), '-e', ROBOT_EMAIL, '-i', str(issue_num),
                '--rev', hash_str, '--private'))
        out = utils.run(cmd, content)
        print('got {} from the run'.format(out))
        line = ""
        for l in out.split('\n'):
            if l.startswith("Issue created"):
                line = l
                break
        if line:
            print("New issue; adding to DB")
            line = line[line.rfind('/') + 1:].strip()
            issue_num = int(line)
            model.set_issue_number(logins, assign, issue_num)    
    finally:
        os.chdir(original_path)

def copy_important_files(assign, start_dir, end_dir, template=False):
    original_path = os.getcwd()
    files_to_copy = get_important_files(assign)
    if template:
        files_to_copy = list(filter(lambda x: x not in new_submit.important_files, files_to_copy))
    # print("copying into dir {} with {}".format(end_dir, os.listdir(end_dir)))
    for filename in files_to_copy:
        shutil.copy(start_dir + filename, end_dir + filename)
    # print("dir is now {}".format(os.listdir(end_dir)))

def put_in_repo(login, assign):
    """
    Puts the login's assignment into their repo
    """
    path_to_subm = get_subm(login, assign)
    logins = open(new_submit.LOGINS_FILE, 'r').read().split('\n')
    path_to_repo = find_path(logins, assign)
    issue_num = model.get_issue_number(logins, assign)
    if not issue_num:
        path_to_template = ASSIGN_DIR
        if "hw" in assign:
            path_to_template += "hw/"
        else:
            path_to_template += "proj/"
        if len(assign) == 3: #wonderful hackage
            assign = assign[:2] + '0' + assign[-1]
        if len(assign) == 5:
            assign = assign[:4] + '0' + assign[-1]
        path_to_template += assign + "/"
        if not os.path.exists(path_to_template):
            raise Exception("Assignment path {} doesn't exist".format(path_to_template))
        copy_important_files(assign, path_to_template, path_to_repo, template=True)
        git.init(path=path_to_repo)
        git.add(None, path=path_to_repo)
        git.commit("Initial commit", path=path_to_repo)
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
    original_path = os.getcwd()
    path_to_repo, logins = put_in_repo(login, assign)
    os.chdir(original_path) #need this because somehow we end up in a bad place now...
    upload(path_to_repo, get_gmails(logins), logins, assign)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds the given login's latest \
     submission for the given assignment to the code review system.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to look at')
    parser.add_argument('login', type=str,
                        help='the login to add')
    args = parser.parse_args()
    add(args.login, args.assign)
