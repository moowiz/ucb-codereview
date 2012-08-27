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

from model import CodeReviewDatabase
model = CodeReviewDatabase(utils.read_db_path())

HOME_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = HOME_DIR + "grading/"
REPO_DIR = GRADING_DIR + "codereview/repo/"
ASSIGN_DIR = HOME_DIR + "lib/"

def get_subm(logins, assign):
    """
    Gets the submission for the given login and assignment
    and moves the current directory to be in the temp directory they're stored in
    """
    tempdir = tempfile.mkdtemp()
    os.chdir(tempdir)
    try:
        out = utils.run("get-subm " + logins[0] + " " + assign)
        print 'hmmm'
        print("out is {}".format(out))
    except OSError as e:
        print >> sys.stderr, str(e)
    return tempdir + "/" #need the trailing slash for the copy command

def find_path(logins, assign):
    """
    Finds the path to the given login's assignment git repository
    """
    path = REPO_DIR + "".join(logins) + "/" + assign + "/"
    exists = False
    try:
        os.makedirs(path)
    except OSError:
        exists = True
    return path, exists

def get_important_files(assign):
    """
    Returns the files we want to copy.
    Do we need this function, or should we copy everything?
    Would involve either some looking at the params file, or looking at the DB
    """
    return model.get_important_file(assign)

def get_sections(logins):
    """
    Returns the sections for logins
    """
    return (201,)

def get_gmails(logins):
    """
    Returns the gmail accounts associated with these students for the code review system.
    Not sure how to do this yet; we'll decide something in the first staff meeting
    """
    return ("stephenmartinis@gmail.com",)

PYTHON_BIN = "python2.7"
UPLOAD_SCRIPT = "~cs61a/code_review/61a-codereview/appengine/upload.py"
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
    -e email of the person
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
    stuff we needed to enter
    first time uploading
    -s (server)
    -t name of assignment 
    -e email for login to uploading (robot)
    -r reviewers (student TA reader other)

    every other time:
    issue number
    revision
    server
    title: timestamp?
    """
    issue_num = model.get_issue_number(logins, assign)
    staff_gmails = tuple(map(lambda x: model.get_reviewers(x), get_sections(logins)))
    content = ""
    if not issue_num:
        cmd = " ".join(PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
            "-t", assign, '-r', " ".join(gmails), " ".join(staff_gmails), '-e', ROBOT_EMAIL)
        content = get_robot_pass()
    else:
        cmd = " ".join(PYTHON_BIN, UPLOAD_SCRIPT, '-s', SERVER_NAME,
            "-t", utils.get_timestamp_str(), '-e', ROBOT_EMAIL, '-i', issue_num,
            '--rev', git.get_revision_hash(path_to_repo))
    out = utils.run(cmd, content)
    line = ""
    for l in out:
        if l.startswith("Issue created:"):
            line = l
            break
    if line:
        line = line[line.rfind('/') + 1:].strip()
        issue_num = int(line)
        model.set_issue_number(logins, assign, issue_num)

def copy_important_files(assign, start_dir, end_dir):
    original_path = os.getcwd()
    files_to_copy = get_important_files(assign)
    for filename in files_to_copy:
        shutil.copy(start_dir + filename, end_dir + filename)
    os.chdir(original_path)
    shutil.rmtree(tempdir)

def put_in_repo(logins, assign):
    """
    Puts the login's assignment into their repo
    """
    tempdir = get_subm(logins, assign)
    path_to_repo, exists = find_path(logins, assign)
    if not exists:
        path_to_template = ASSIGN_DIR
        if "hw" in assign:
            path_to_template += "hw/"
        else:
            path_to_template += "proj/"
        path_to_template += assign + "/"
        if len(assign) == 3:
            assign = assign[:2] + '0' + assign[-1]
        if len(assign) == 5:
            assign = assign[:4] + '0' + assign[-1]
        if not os.path.exists(path_to_template):
            raise Exception("Assignment path {} doesn't exist".format(path_to_template))
        copy_important_files(assign, path_to_template, path_to_repo)
        git.add(None, path=path_to_repo)
        git.commit("Initial commit", path=path_to_repo)
    copy_important_files(assign, tempdir, path_to_repo)
    git.add(None, path=path_to_repo)
    git.commit("{} commit of code".format(utils.get_timestamp_str()), path=path_to_repo)
    return path_to_repo

def add(logins, assign):
    path_to_repo = put_in_repo(logins, assign)
    upload(path_to_repo, get_gmails(logins), logins, assign)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds the given login's latest \
     submission for the given assignment to the code review system.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to look at')
    parser.add_argument('logins', type=str, nargs='*',
                        help='the login(s) to add')
    args = parser.parse_args()
    add(args.logins, args.assign)