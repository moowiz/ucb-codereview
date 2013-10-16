import base
import argparse 

parser = argparse.ArgumentParser(description="Upgrade old schema to add a semester field")
args = base.init(parser)

from codereview.models import Issue, Account
import collections

def find_all():
    seen = collections.defaultdict(list)
    count = 0
    for acc in Account.all():
        seen[acc.lower_email].append(acc)
        if count % 10 == 0:
            print count
        count += 1
    print [(k, v) for k,v in seen.items() if len(v) > 1]

        

def main():
    find_all()

if __name__ == "__main__":
    main()

