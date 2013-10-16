#!/usr/bin/python

import base
import argparse
parser = argparse.ArgumentParser(description="Gets the composition scores for an assignment")
parser.add_argument('assignment', type=str,
                    help='the assignment to grade')
parser.add_argument('semester', type=str,
                    help='the semester from which to get assignments to grade')
parser.add_argument('-f', '--file', type=str,
                    help='the file to write the grades to')
args = base.init(parser)

from codereview.models import Issue

grades = {}
def main():
    good = seen = 0
    for issue in Issue.all().filter('subject =', args.assignment).filter('semester =', args.semester):
        seen += 1
        if issue.comp_score > -1:
            for stu in issue.owners:
                good += 1
                grades[stu] = issue.comp_score
        if seen % 50 == 0 or good % 50 == 0:
            print "good {} seen {}".format(good, seen)
    for k in grades:
        print "{} : {}".format(k, grades[k])
    if args.file:
        with open(args.file, 'w') as f:
            for k in grades:
                f.write("{} : {}\n".format(k, grades[k]))


if __name__ == "__main__":
    main()
