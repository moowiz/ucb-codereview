import argparse
import sys
import os
import getpass
from google.appengine.ext.remote_api import remote_api_stub

cwd = os.getcwdu()
cwd = "/".join(cwd.split("/")[:-1]) + "/appengine"
sys.path.append(cwd)
#Idk what this is about....
os.environ['SERVER_SOFTWARE'] = ''

def auth_func():
    return (u'moowiz2020@gmail.com', getpass.getpass(u'Password:'))

remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func, 'ucb-codereview.appspot.com')
from codereview.models import Issue, Account

def find_all(assign):
    with open('out', 'w') as f:
        issues = Issue.all().filter(u'subject =', assign).fetch(100)
        for iss in issues:
            #print iss.reviewers
            acc = [Account.get_account_for_email(stu) for stu in iss.reviewers]
            #print acc
            acc = [a for a in acc if len(str(a)) > 4]
            #print [a.email for a in acc]
            sections = [a.sections for a in acc]
            if sections:
                all_sections = set(reduce(lambda a, b: a + b, sections))
                #print all_sections
                if len(set(all_sections)) > 1:
                    val = iss.key().id()
                    print val, iss.sections
                    f.write("{} {}\n".format(val, iss.sections))
            else:
                print 'uhoh'
                print iss.sections
        

def main(assign):
    find_all(assign)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Finds all issues which have students from different sections")
    parser.add_argument('assign', type=str,
                        help='the assignment to grade')
    args = parser.parse_args()
    main(args.assign)

