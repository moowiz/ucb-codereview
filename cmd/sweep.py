""" This script will be cron'd (?)
    It will find the submissions that have not been uploaded and upload them
"""
import os
import utils
import argparse
import add_subm
import sys

from model import CodeReviewDatabase
model = CodeReviewDatabase(utils.read_db_path())

HOME_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = HOME_DIR + "grading/"
SUBMISSION_DIR = GRADING_DIR + "submission/"

def sweep(assign):
    if assign == "all":
        dirs = os.listdir(SUBMISSION_DIR)    
    else:
        dirs = [assign]
    latest = model.last_uploaded()
    if not latest:
        latest = float("-inf")
    print(latest)
    logins = {}
    max = float("-inf")
    for directory in dirs:
        subms = os.listdir(SUBMISSION_DIR + "/" + directory)
        latest = model.last_uploaded()
        logins[directory] = []
        for name in subms:
            splt = name.split(".")
            login = splt[0]
            timestamp = int(splt[1])
            if (timestamp > latest):
                logins[directory].append(login)
            if (timestamp > max):
                max = timestamp
      
    model.set_last_uploaded(max)
    return logins

def main(assign, add):
    logins = sweep(assign)
    if add:
        print('yay')
        sys.exit(0)
        for k, v in logins.items():
            for login in v:
                add_subm.add([login], k) 
    else:
        print(logins)  


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submits the assignment, \
        assuming the correct files are in the given directory.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to submit, or "all" for all assignments')
    parser.add_argument("-a", "--add" action="store_true",
                    help="runs add.py on all inputs")
    args = parser.parse_args()
    main(args.assign, args.add)
