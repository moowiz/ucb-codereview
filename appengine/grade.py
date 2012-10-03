import re
import logging

from codereview.models import Issue

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import mail

#a regex to filter out lines that are always at the top of the message
REGEX = re.compile(r'http://.*\.appspot\.com/[0-9]{5}/diff/[0-9]+/[a-zA-Z_]+\.py(#.*)*')

GRADES = {u'very nice' : 2,
            u'excellent' : 3,
            u'ok' : 0,
            u'good job' : 1}

def is_grade(text_arr):
    text_arr = list(map(lambda x: x.lower().replace("!","").replace(".", "").replace(",", ""), text_arr))
    text = [" ".join(list(map(lambda x: x.lower(), text_arr))).replace("!", "").replace(".", "")]
    text.extend(text_arr[:])
    for grade in GRADES:
        if grade in text:
            return GRADES[grade]

"""
http://berkeley-61a.appspot.com/21161/diff/3001/hog.py File hog.py (right): http://berkeley-61a.appspot.com/21161/diff/3001/hog.py#newcode1 hog.py:1: \"\"\"The Game of Hog\"\"\" Very nice! 
http://berkeley-61a.appspot.com/46070/diff/1003/hog.py File hog.py (right): http://berkeley-61a.appspot.com/46070/diff/1003/hog.py#newcode1 hog.py:1: 61A Project 1 Excellent!
"""

__TEXT = []

def grade():
    logging.info("Grading")
    issues = db.GqlQuery("SELECT * FROM Issue WHERE subject='proj1'")
    for issue in issues:
        message = db.GqlQuery("SELECT * FROM Message WHERE issue = :1 AND draft = false", issue)
        for m in message:
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
                    #fill this in
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

def my_mail():
    address = "cs61a-ty@imail.eecs.berkeley.edu"
    subject = "grades"
    body = "".join(__TEXT)
    mail.send_mail("moowiz2020@gmail.com", address, subject, body)
    __TEXT[:] = []
        
def found_grade(issue, grade):
    __TEXT.append("{} : {}\n".format(issue.key().id(), grade))

def main(env, response):
    grade()
    my_mail()
