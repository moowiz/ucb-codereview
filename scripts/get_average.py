import base
import argparse

parser = argparse.ArgumentParser(description="Get average grades for each reader")
args = base.init(parser)

from codereview.models import Issue, Account, Semester

def main():
    sem = Semester.all().get()

    readers = Account.all().ancestor(sem).filter('role =', 1).run()

    grade_mapping = {}      # mapping of reader email to average grade
    reader_mapping = {}     # mapping of student login to reader login
    login_to_email = {}

    with open('data') as data_f:
        for line in data_f:
            login, email = [x.strip() for x in line.split(',')]
            login_to_email[login] = email

    for reader in readers:
        print reader.email
        stus = list(Account.all().ancestor(sem).filter('reader = ', reader).run())
        issues = []
        for stu in stus:
            reader_mapping[stu.email] = reader.email
            issues.extend(list(Issue.all().filter("semester =", sem.name).filter('subject =', 'proj1').filter('owners =', stu.email).run()))

        grade_mapping[reader.email] = float(sum(iss.comp_score for iss in issues if iss.comp_score > -1)) / len(issues)

    print grade_mapping
    print reader_mapping
    print login_to_email

if __name__ == '__main__':
    main()