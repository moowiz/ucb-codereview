import os
import sys
import getpass
import argparse
from google.appengine.ext.remote_api import remote_api_stub
from google.appengine.api.users import User

cwd = os.getcwdu()
cwd = "/".join(cwd.split("/")[:-1]) + "/appengine"
sys.path.append(cwd)
#Idk what this is about....
os.environ['SERVER_SOFTWARE'] = ''

def auth_func():
    return (u'moowiz2020@gmail.com', u'twyibazqjqpsqvph')

parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
parser.add_argument('mapping', type=str,
                    help='the path to the csv file containing email to section mappings')
parser.add_argument('host', type=str,
                    help='the URL of the server we want to upload info to')
args = parser.parse_args()
remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func, args.host)
from codereview.models import Account

def make_acc(email, section):
    acc = Account.get_or_insert('<%s>' % email, user=User(email), email=email)
    section = int(section)
    if section not in acc.sections:
        acc.sections.append(section)
    acc.put()

def main(filename):
    f = open(os.path.expanduser(filename))
    split = f.read().split('\r')
    split = list(map(lambda x: x.strip().split(','), split))
    f.close()
    count = 0
    for it in split:
        if count % 10 == 0:
            print 'counter {}'.format(count)
        if count > 20:
            return
        make_acc(it[0], it[1])
        count += 1

if __name__ == "__main__":
    main(args.mapping)
