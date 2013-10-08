from google.appengine.api.users import User
from google.appengine.ext import db

from utils import TestCase

from codereview import models, views

TEST_EMAIL = "aeotuhnarcuonetb@gmail.com"

class AccountTest(TestCase):
	def test_account_create(self):
		test_sections = [28]
		test_semester = ['sp13']
		acc = models.Account(email=TEST_EMAIL, semesters=test_semester, sections=test_sections, user=User(TEST_EMAIL))
		acc.save()
		acc.put()
