#!/bin/python3
import argparse
import os

email_to_login = {}
for path, __, files in os.walk(os.path.expanduser('~/grading/register/')):
	for file in files:
		with open(os.path.join(path, file)) as open_file:
			lines = open_file.read().split('\n')
			while 'Email' not in lines[0]:
				lines = lines[1:]
			email_line = lines[0]
			email = email_line[email_line.find(':')+1:].strip()
			print('email "{}" login "{}"'.format(email, file))
			email_to_login[email] = file

parser = argparse.ArgumentParser(description="Transforms raw grades into grades that can be put into glookup")
parser.add_argument('file', type=str)
parser.add_argument('out_file', type=str)
args = parser.parse_args()

with open(args.file) as open_file:
	with open(args.out_file, 'w') as out_file:
		for line in open_file:
			email, grade = line.split(':')
			grade = int(grade.strip())
			email = email.strip()
			try:
				out_file.write('{} a {}\n'.format(email_to_login[email], grade))
			except:
				print('ERR: couldn\'t write grade for ', email)
