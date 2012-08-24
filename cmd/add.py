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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds the given login's latest submission for the given assignment to the code review system.")
    parser.add_argument('login', type=str,
                        help='the login to add')
    parser.add_argument('assign', type=str,
                        help='the assignment to look at')
    args = parser.parse_args()
    original_path = os.getcwd()
    tempdir = get_subm(args.login, args.assign)
    path_to_repo = find_path(login, assign)
    files_to_copy = get_important_files(assign)
    for filename in files_to_copy:
        shutil.copy(tempdir + filename, path_to_repo + filename)
    os.chdir(original_path)
    shutil.rmtree(tempdir)