#!/bin/python3
import argparse

email_to_login = {}
for _, __, files in os.walk(os.path.expanduser('~/grading/register/'))
	for file in files:
		with open(file) as open_file:
			lines = open_file.split('\n')
			while 'Email' not in lines[0]:
				lines = lines[1:]
			email_line = lines[0]
			email = email_line[email_line.find(':'):].strip()
			login_to_email[email] = login

parser = argparse.ArgumentParser(description="Transforms raw grades into grades that can be put into glookup")
parser.add_argument('file', type=str)
parser.add_argument('out_file', type=str)
args = parser.parse_args()

with open(args.file) as open_file:
	with open(args.out_file, 'w') as out_file:
		for line in open_file:
			email, grade = line.split(':')
			grade = int(grade)
			out_file.write('{} a {}'.format(email_to_login[email], grade))
