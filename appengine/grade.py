import re

from google.appengine.ext import db
from google.appengine.api import users

#a regex to filter out lines that are always at the top of the message
REGEX = re.compile(r'http://.*\.appspot\.com/[0-9]{5}/diff/[0-9]+/[a-zA-Z_]+\.py(#.*)*')

GRADES = {"very nice" : 2,
            "excellent" : 3,
            "ok" : 0,
            "good job" : 1}

def is_grade(text_arr):
    text_arr = list(map(lambda x: x.lower().replace("!","").replace(".", ""), text_arr))
    text = [" ".join(list(map(lambda x: x.lower(), text_arr))).replace("!", "").replace(".", "")]
    text.extend(text_arr[:])
    print("text is {}".format(text))
    for grade in GRADES:
        if grade in text:
            return GRADES[grade]
    return None

"""
http://berkeley-61a.appspot.com/46070/diff/1003/hog.py File hog.py (right): http://berkeley-61a.appspot.com/46070/diff/1003/hog.py#newcode1 hog.py:1: 61A Project 1 Excellent!
"""

def grade():
    issues = db.GqlQuery("SELECT subject FROM Issue WHERE description='proj1'").Run()
    for issue in issues:
        message = db.GqlQuery("SELECT text, draft, sender FROM Message WHERE issue = :1", issue).filter("draft = ", False)
        for m in message:
            mtext = m.text.split(" ")
            if is_grade(mtext[:2]):
                found_grade(is_grade(mtext[:2]))
                break
            else:
                if not REGEX.match(mtext[0]): #the first thing needs to be the url thing
                    continue
                else:
                    pass
        else:
            print("ERROR: didn't find a grade for issue {}".format(issue))

        
def found_grade(issue):
    print("found a grade!")




