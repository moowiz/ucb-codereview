#!/bin/python3
import argparse
import os

parser = argparse.ArgumentParser(description="Transforms raw grades into grades that can be put into glookup")
parser.add_argument('file', type=str, help="The file with raw grades")
parser.add_argument('out_file', type=str, help="The file to write the resulting grades to")
parser.add_argument('assignment', type=str, help="The assignment you're grading")
args = parser.parse_args()

if __name__ == "__main__":
    email_to_login = {}
    for path, __, files in os.walk(os.path.expanduser('~/grading/register/')):
        for file in files:
            with open(os.path.join(path, file)) as open_file:
                lines = open_file.read().split('\n')
                while 'Email' not in lines[0]:
                    lines = lines[1:]
                email_line = lines[0].lower()
                email = email_line[email_line.find(':')+1:].strip()
                email_to_login[email] = file

    with open(args.file) as open_file:
        with open(args.out_file, 'w') as out_file:
            for line in open_file:
                email, grade = line.split(':')
                grade = int(grade.strip())
                email = email.strip()
                try:
                    out_file.write('{} {} {}\n'.format(email_to_login[email], args.assignment, grade))
                except:
                    print('ERR: couldn\'t write grade for', email, ' grade was', grade)
