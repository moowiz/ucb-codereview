import base
parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
parser.add_argument('mapping', type=str,
                    help='the path to the csv file containing email to section mappings')
args = base.init(parser)

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
        break

if __name__ == "__main__":
    main(args.mapping)
