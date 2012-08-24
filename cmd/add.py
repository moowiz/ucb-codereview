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

HOME_DIR = '~cs61a/'
GRADING_DIR = HOME_DIR + "grading/"
SUBMISSION_DIR = GRADING_DIR + 'submissions/'

def get_subm(login, assign):
    """
    Gets the submission for the given login and assignment
    and moves the current directory to be in the temp directory they're stored in
    """
    tempdir = tempfile.mkdtemp()
    os.chdir(tempdir)
    try:
        utils.run("get-subm " + login + " " + assign)
    except OSError as e:
        print << sys.stderr, str(e)
    return tempdir + "/" #need the trailing slash for the copy command

def find_path(login, assign):
    """
    Finds the path to the given login's assignment git repository
    Not sure how we're structuring this right now...
    """
    return ""

def get_important_files(assign):
    """
    Returns the files we want to copy.
    Do we need this function, or should we copy everything?
    Would involve either some looking at the params file, or looking at the DB
    """
    return [""]

def get_gmail(login):
    """
    Returns the gmail account associated with this student for the code review system.
    Not sure how to do this yet; we'll decide something in the first staff meeting
    """
    return "example@gmail.com"

def upload(path_to_repo, gmail):
    """
    Calls the upload script with the needed arguments given the path to the repo and the
    gmail account of the student.
    Arguments we care about:
    -e email of the person
    -r reviewers
    --cc people to cc
    --private makes the issue private 
    --send_mail sends an email to the reviewers (might want)
    --send_patch sends an email but with the diff attached, possible thing to do
    """
    return

def put_in_repo(login, assign):
    original_path = os.getcwd()
    tempdir = get_subm(login, assign)
    path_to_repo = find_path(login, assign)
    files_to_copy = get_important_files(assign)
    for filename in files_to_copy:
        shutil.copy(tempdir + filename, path_to_repo + filename)
    os.chdir(original_path)
    shutil.rmtree(tempdir)
    return path_to_repo

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds the given login's latest submission for the given assignment to the code review system.")
    parser.add_argument('login', type=str,
                        help='the login to add')
    parser.add_argument('assign', type=str,
                        help='the assignment to look at')
    args = parser.parse_args()
    path_to_repo = put_in_repo(args.login, args.assign)
    upload(path_to_repo, get_gmail(args.login))