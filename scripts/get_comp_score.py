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
    for issue in Issue.all().filter('subject =', 'proj1'):
        if issue.comp_score > -1:
            for stu in issue.reviewers:
                grades[stu] = issue.comp_score
    for k in grades:
        print "{} : {}".format(k, grades[k])

if __name__ == "__main__":
    main()
