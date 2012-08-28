""" This script will be cron'd (?)
    It will find the submissions that have not been uploaded and upload them
"""
import os
import utils
import argparse
import add_subm
import sys
import datetime
import calendar

from model import CodeReviewDatabase
model = CodeReviewDatabase(utils.read_db_path())

HOME_DIR = os.path.expanduser('~cs61a/')
GRADING_DIR = HOME_DIR + "grading/"
SUBMISSION_DIR = GRADING_DIR + "submissions/"

def get_small_datetime():
    return 1000000

def conv_timestamp(time_str):
    #format is 201208261827, return a date
    #          012345678901
    # datetime.datetime
    year = int(time_str[:4])
    month = int(time_str[4:6])
    day = int(time_str[6:8])
    hour = int(time_str[8:10])
    minute = int(time_str[10:])
    return calendar.timegm(datetime.datetime(year, month, day, hour=hour, minute=minute).timetuple())

def get_last_uploaded():
    latest = model.last_uploaded()
    if not latest:
        latest = get_small_datetime()
    return latest

def sweep(assign):
    if assign == "all":
        dirs = os.listdir(SUBMISSION_DIR)    
    else:
        dirs = [assign]
    latest = get_last_uploaded()
    print(latest)
    logins = {}
    max = get_small_datetime()
    for directory in dirs:
        subms = os.listdir(SUBMISSION_DIR + directory)
        latest = get_last_uploaded()
        logins[directory] = []
        for name in subms:
            splt = name.split(".")
            login = splt[0]
            timestamp = conv_timestamp(splt[1])
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
    parser.add_argument("-a", "--add", action="store_true",
                    help="runs add.py on all inputs")
    args = parser.parse_args()
    main(args.assign, args.add)
