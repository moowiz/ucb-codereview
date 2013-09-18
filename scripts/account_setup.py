import base
import argparse 
import os

parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
parser.add_argument('mapping', type=str,
                    help='the path to the csv file containing email to section mappings')
args = base.init(parser)

from codereview.models import Account
from google.appengine.api import users
CURRENT_SEMESTER = "fa13"

def make_acc(email, section):
    acc = Account.get_or_insert('<%s>' % email, user=users.User(email), email=email)
    section = int(section)
    if section not in acc.sections:
        acc.sections.append(section)
    if CURRENT_SEMESTER not in acc.semesters:
        acc.semesters.append(CURRENT_SEMESTER)
    acc.put()

def main(filename):
    with open(filename) as f:
        split = f.read().split('\r')
        split = list(map(lambda x: x.strip().split(','), split))

    count = 0
    for it in split:
        if count % 10 == 0:
            print 'counter {}'.format(count)
        make_acc(it[0], it[1])
        count += 1

if __name__ == "__main__":
    main(os.path.expanduser(args.mapping))
