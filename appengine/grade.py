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

def my_mail():
    address = "cs61a-ty@imail.eecs.berkeley.edu"
    subject = "grades"
    body = "".join(__TEXT)
    mail.send_mail("moowiz2020@gmail.com", address, subject, body)
    __TEXT[:] = []


def main(env, response):
    grade()
    my_mail()
