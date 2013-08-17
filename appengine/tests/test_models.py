from google.appengine.api.users import User

from utils import TestCase

from codereview import models, views

TEST_EMAIL = "aeotuhnarcuonetb@gmail.com"

class AccountTest(TestCase):
	def testAccountCreate(self):
		test_sections = [28]
		test_semester = ['sp13']
		acc = models.Account(email=TEST_EMAIL, semesters=test_semester, sections=test_sections)
		acc.put()

		sec = models.Section.get('<{}>'.format(test_sections[0]))
		assert sec is not None
