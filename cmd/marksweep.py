""" This script will be cron'd (?)
    It will find the submissions that have not been uploaded and upload them
"""
import os
import utils
import argparse

from model import CodeReviewDatabase
model = CodeReviewDatabase(utils.read_db_path())

HOME_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = HOME_DIR + "grading/"
SUBMISSION_DIR = HOME_DIR + "submissions/"

def mark():
    dirs = os.listdir(SUBMISSION_DIR)
    latest = float("-inf")
    for name in dirs:
        splt = name.split(".")
        login = splt[0]
        timestamp = int(splt[1])
        if (timestamp > latest):
            latest = timestamp
    print("latest",latest)
    model.set_last_uploaded(latest)
    
def sweep():
    dirs = os.listdir(SUBMISSION_DIR)
    latest = model.last_uploaded()
    logins = []
    for name in dirs:
        splt = name.split(".")
        login = splt[0]
        timestamp = int(splt[1])
        if (timestamp > latest):
            logins.append(login)
    return logins        

def main(assign):
    logins = sweep()
    mark()
    print(logins)  

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submits the assignment, \
        assuming the correct files are in the given directory.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to submit')
    args = parser.parse_args()
    main(args.assign)
