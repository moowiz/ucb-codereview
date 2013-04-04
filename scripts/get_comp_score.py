#!/usr/bin/python
import os
import sys
import getpass
import argparse
from google.appengine.ext.remote_api import remote_api_stub

cwd = os.getcwdu()
cwd = "/".join(cwd.split("/")[:-1]) + "/appengine"
sys.path.append(cwd)
#Idk what this is about....
os.environ['SERVER_SOFTWARE'] = ''

def auth_func():
    return (u'moowiz2020@gmail.com', getpass.getpass("Google One time password:"))

parser = argparse.ArgumentParser(description="Gets the composition scores for an assignment")
parser.add_argument('assignment', type=str,
                    help='the assignment to grade')
parser.add_argument('host', type=str,
                    help='the URL of the server we want to upload info to')
args = parser.parse_args()
remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func, args.host)
from codereview.models import Issue

grades = {}
def main():
    good = seen = 0
    for issue in Issue.all().filter('subject =', args.assignment):
        seen += 1
        if issue.comp_score > -1:
            for stu in issue.reviewers:
                good += 1
                grades[stu] = issue.comp_score
        if seen % 50 == 0 or good % 50 == 0:
            print "good {} seen {}".format(good, seen)
    for k in grades:
        print "{} : {}".format(k, grades[k])

if __name__ == "__main__":
    main()
