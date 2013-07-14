import base
import argparse
parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
args = base.init(parser)

from codereview.models import Issue, Account
from google.appengine.ext import db

def find_all():
	all_ = []
	count = 0
	iterr = iter(db.GqlQuery("SELECT * FROM Issue WHERE subject=:1", "proj1").run(batch_size=400))
	try:
		while True:
			a = next(iterr)
			print a
			a.semester = u'sp13'
			print count
			count += 1
			all_.append(a)
	except StopIteration:
		pass
	db.put(all_)
        

def main():
    find_all()

if __name__ == "__main__":
    main()

