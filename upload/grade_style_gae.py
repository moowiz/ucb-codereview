import argparse
import sys
import os
import re
import getpass
from google.appengine.ext.remote_api import remote_api_stub

cwd = os.getcwdu()
cwd = "/".join(cwd.split("/")[:-1]) + "/appengine"
sys.path.append(cwd)
#Idk what this is about....
os.environ['SERVER_SOFTWARE'] = ''

def auth_func():
    return (u'moowiz2020@gmail.com', getpass.getpass(u'Password:'))

remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func, 'berkeley-61a.appspot.com')
from codereview.models import Message, Issue

REGEX = re.compile(r'http://.*\.appspot\.com/[0-9]{5}/diff/[0-9]+/[a-zA-Z_]+\.py(#.*)*')

GRADES = {u'very nice' : 2,
          u'very good' : 2,
          u'excellent' : 3,
          u'ok' : 0,
          u'good job' : 1}

__TEXT = []

def is_grade(text_arr):
    text_arr = list(map(lambda x: x.lower().replace("!","").replace(".", "").replace(",", ""), text_arr))
    text = [" ".join(list(map(lambda x: x.lower(), text_arr))).replace("!", "").replace(".", "")]
    text.extend(text_arr[:])
    for grade in GRADES:
        if grade in text:
            return GRADES[grade]

def grade(assign):
    issues = Issue.all().filter(u'subject =', assign).fetch(None)
    counter = 0
    for issue in issues:
        messages = Message.all().filter("issue = ", issue).fetch(None)
        if counter % 30 == 0:
            print "Downloaded ", counter
        counter += 1
        for m in messages:
            mtext = m.text.split()
            if len(mtext) < 1:
                continue
            grade = is_grade(mtext[:2])
            if grade:
                found_grade(issue, grade)
                break
            else:
                if not REGEX.match(mtext[0]): #the first thing needs to be the url thing
                    continue
                else:
                    ind, count = 3, 0
                    while ind < len(mtext):
                        if ".py" in mtext[ind]:
                            if count > 0:
                                ind += 1
                                break
                            else:
                                count += 1
                        ind += 1
                    if "\"\"\"" in mtext[ind]:
                        ind += 1
                        while ind < len(mtext):
                            if "\"\"\"" in mtext[ind]:
                                count += 1
                                break
                            ind += 1
                    grade = is_grade(mtext[ind:ind+2])
                    if grade:
                        found_grade(issue, grade)
        else:
            found_grade(issue, None)

def found_grade(issue, grade):
    __TEXT.append("{} : {}".format(issue.key().id(), grade))

def main(assign):
    grade(assign)
    for it in __TEXT:
        print it

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grades the style for a given assignment")
    parser.add_argument('assign', type=str,
                        help='the assignment to grade')
    args = parser.parse_args()
    main(args.assign)
