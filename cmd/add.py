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

HOME_DIR = '~cs61a/'
GRADING_DIR = HOME_DIR + "grading/"
SUBMISSION_DIR = GRADING_DIR + 'submissions/'

def get_subm(login, assign):
    #something like this
    """
    os.make_tmp_dir() #or some similar command
    try:
        os.system(["get-subm", login, assign])
    except OSError:
        print << sys.stderr, "Some error message"
    """

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adds the given login's latest submission for the given assignment to the code review system.")
    parser.add_argument('login', type=str,
                        help='the login to add')
    parser.add_argument('assign', type=str,
                        help='the assignment to look at')
    args = parser.parse_args()
    get_subm(args.login, args.assign)