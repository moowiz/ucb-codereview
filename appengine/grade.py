import re
import logging

from google.appengine.ext import db
from google.appengine.api import users

#a regex to filter out lines that are always at the top of the message
REGEX = re.compile(r'http://.*\.appspot\.com/[0-9]{5}/diff/[0-9]+/[a-zA-Z_]+\.py(#.*)*')

GRADES = {u'very nice' : 2,
            u'excellent' : 3,
            u'ok' : 0,
            u'good job' : 1}

def is_grade(text_arr):
    text_arr = list(map(lambda x: x.lower().replace("!","").replace(".", ""), text_arr))
    text = [" ".join(list(map(lambda x: x.lower(), text_arr))).replace("!", "").replace(".", "")]
    text.extend(text_arr[:])
    for grade in GRADES:
        if grade in text:
            return GRADES[grade]

"""
http://berkeley-61a.appspot.com/46070/diff/1003/hog.py File hog.py (right): http://berkeley-61a.appspot.com/46070/diff/1003/hog.py#newcode1 hog.py:1: 61A Project 1 Excellent!
"""

def grade():
    logging.info("Grading")
    issues = db.GqlQuery("SELECT * FROM Issue WHERE subject='proj1'")
    logging.info("issues {}".format(str(issues)[:100]))
    for issue in issues:
        logging.info("issue {}".format(issue))
        message = db.GqlQuery("SELECT * FROM Message WHERE issue = :1 AND draft = false", issue)
        for m in message:
            logging.info("message {}".format(m.text))
            mtext = m.text.replace("\n", " ").replace("\r", " ").split(" ")
            grade = is_grade(mtext[:2])
            if grade:
                found_grade(issue, grade)
                break
            else:
                if not REGEX.match(mtext[0]): #the first thing needs to be the url thing
                    continue
                else:
                    #fill this in
                    pass
        else:
            print("ERROR: didn't find a grade for issue {}".format(issue))

        
def found_grade(issue, grade):
    out = ""
    for person in issue.reviewers:
        out += "{} : {}\n".format(person, grade)
    print(out)

def main(env, response):
    grade()
