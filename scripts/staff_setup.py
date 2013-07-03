import base
import argparse

parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
parser.add_argument('mapping', type=str,
                    help='the path to the csv file containing email to section mappings')
args = base.init(parser)
#remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', auth_func, args.host)
from codereview.models import Account

def make_acc(email, section):
    section = int(section)
    username = email[:email.find('@')]
    acc = Account.get_or_insert('<%s>' % email, user=User(username), email=email)
    acc.is_staff = True
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
        make_acc(it[0], it[1])
        count += 1

if __name__ == "__main__":
    main(args.mapping)
