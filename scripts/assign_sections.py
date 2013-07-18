import base
import argparse

parser = argparse.ArgumentParser(description="Randomly assigns sections to people that don't have any")
args = base.init(parser)

from codereview.models import Account
import random

all_sections = list(range(101,109))
def main():
    accs = Account.all().filter('semester =', args.semester)
    done = 0
    for i, acc in enumerate(accs):
        if i % 100 == 0:
            print 'i {} done {}'.format(i, done)
        if not acc.sections:
            acc.sections = [random.choice(all_sections)]
            acc.put()
            done += 1

if __name__ == "__main__":
    main()

