import base
import argparse
import os


from codereview.models import Account
from google.appengine.api import users
CURRENT_SEMESTER = "fa13"

def make_acc(email, section, staff):
    acc = Account.get_or_insert('<%s>' % email, user=users.User(email), email=email)
    section = int(section)
    if staff:
        acc.is_staff = True
    if section not in acc.sections:
        acc.sections.append(section)
    if CURRENT_SEMESTER not in acc.semesters:
        acc.semesters.append(CURRENT_SEMESTER)
    acc.put()

def main(filename, staff=False):
    with open(filename) as f:
        split = f.read().split('\r')
        split = list(map(lambda x: x.strip().split(','), split))

    count = 0
    for it in split:
        if count % 10 == 0:
            print 'counter {}'.format(count)
        make_acc(it[0], it[1], staff)
        count += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
    parser.add_argument('mapping', type=str,
                        help='the path to the csv file containing email to section mappings. \
                             The email should be in the first column, and the section number should be in the second column')
    args = base.init(parser)

    main(os.path.expanduser(args.mapping))
