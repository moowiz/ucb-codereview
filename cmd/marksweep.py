""" This script will be cron'd (?)
    It will find the submissions that have not been uploaded and upload them
"""
import os
import utils

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

             

if __name__ == "__main__":
    logins = sweep()
    mark()
    print(logins)
