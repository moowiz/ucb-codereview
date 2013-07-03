import base
import argparse
parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
args = base.init(parser)

from codereview.models import Issue, Account

def find_all():
    with open('out', 'w') as f:
        issues = Issue.all()
        for iss in issues.fetch(10):
            print(iss.semester)
        

def main():
    find_all()

if __name__ == "__main__":
    main()

