import base
import argparse
import os


from codereview.models import Account
from google.appengine.api import users
CURRENT_SEMESTER = "sp14"

def make_acc(email, role, staff):
    acc = Account.get_account_for_user(users.User(email))
    role = int(role)
    if staff:
        acc.role = role
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


# TODO: add support for different semesters
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
    parser.add_argument('mapping', type=str,
                        help='the path to the csv file containing email to role mappings, where 1 corresponds to a reader, and 2 to a TA \
                             The email should be in the first column, and the section number should be in the second column')
    args = base.init(parser)

    main(os.path.expanduser(args.mapping))
