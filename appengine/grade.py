import re

from google.appengine.ext import db
from google.appengine.api import users

#a regex to filter out lines that are always at the top of the message
REGEX = re.compile(r'http://.*\.appspot\.com/[0-9]{5}/diff/[0-9]+/[a-zA-Z_]+\.py')

GRADES = {"very nice" : 2,
            "excellent" : 3,
            "ok" : 0
            "good job" : 1}

def is_grade(text_arr):
    text = " ".join(list(map(lambda x: x.lower(), text_arr))).replace("!", "").replace(".", "")
    return any(map(lambda x: text in x, GRADES.keys()))

def grade():
    test = ("http://berkeley-61a.appspot.com/1111/diff/12/hog.py",
                "http:/berkeley-61a.appspot.com/11123/diff/a/hog.py",
                "http://berkeley-61a.appspot.com/12345/diff/5/bill.txt",
                "http://berkeley-61a.appspot.com/12345/diff/6/hog.py")
    for t in test:
        print("{} passes? {}".format(t, True if REGEX.match(t) else False))
    issues = db.GqlQuery("SELECT subject FROM Issue WHERE description='proj1'").Run()
    for issue in issues:
        message = db.GqlQuery("SELECT text, draft, sender FROM Message WHERE issue = :1", issue).split(" ")
        if is_grade(message.text[:2]):
            #found a grade
        else:
            #other stuff
        




