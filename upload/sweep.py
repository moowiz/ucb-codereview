""" This script will be cron'd (?)
    It will find the submissions that have not been uploaded and upload them
"""
import os
import utils
import argparse
import add_subm
import datetime
import calendar
from config import *

from model import CodeReviewDatabase
model = CodeReviewDatabase(config.DB_PATH)

def get_small_time():
    return 1000 #randomly chosen. Guaranteed to be small :)

def conv_timestamp(time_str):
    #format is 201208261827, return a date
    year = int(time_str[:4])
    month = int(time_str[4:6])
    day = int(time_str[6:8])
    hour = int(time_str[8:10])
    minute = int(time_str[10:])
    return calendar.timegm(datetime.datetime(year, month, day, hour=hour, minute=minute).timetuple())

def get_last_uploaded(assign):
    latest = model.last_uploaded(assign)
    # print("latest {}".format(latest))
    if not latest:
        return get_small_time()
    return latest

def sweep(assign, first):
    if assign == "all":
        dirs = os.listdir(config.SUBMISSION_DIR)
    else:
        dirs = [assign]
    logins = {}
    max = get_small_time()
    maxes = {}
    for directory in dirs:
        subms = filter(lambda x: not os.path.islink(config.SUBMISSION_DIR + x), os.listdir(config.SUBMISSION_DIR + directory))
        latest = get_last_uploaded(directory)
        logins[directory] = set()
        for name in subms:
            splt = name.split(".")
            login = splt[0]
            if not login:
                continue
            if not splt[1].isdigit():
                print("Warning: Ignoring " + login +"'s submission")
                continue
            timestamp = conv_timestamp(splt[1])
            if (timestamp >= latest) and (not first or not model.get_issue_number(login, assign)):
                logins[directory].add(login)
                if (timestamp > max):
                    max = timestamp
        maxes[directory] = max
    return logins, maxes

def main(assign, add, first, semester):
    utils.check_allowed_user()
    original_dir = os.getcwd()
    logins, maxes = sweep(assign, first)
    if add:
        os.chdir(original_dir)
        for assign, logins in logins.items():
            for login in logins:
                try:
                    add_subm.add(login, assign, semester)
                except Exception as e:
                    print("Exception {}".format(e))
                    del maxes[assign]
        for assign, time in maxes.items():
            model.set_last_uploaded(time, assign)
    else:
        for key, value in logins.items():
            print('assignment {}'.format(key))
            for item in value:
                print(item)
            print("Number to upload: {}".format(len(value)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submits the assignment, \
        assuming the correct files are in the given directory.")
    parser.add_argument('assign', type=str,
                        help='the assignment to submit, or "all" for all assignments')
    parser.add_argument("-a", "--add", action="store_true",
                        help="runs add_subm.py on all inputs")
    parser.add_argument('-s', '--semester', type=str,
                       help="the semester to upload all the issues to")
    parser.add_argument('--first', action='store_true', help='First run; this means that \
                        if someone is already in the system then we don\'t add them again')
    args = parser.parse_args()
    main(args.assign, args.add, args.first, args.semester)
