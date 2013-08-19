from google.appengine.api.users import User
from google.appengine.ext import db

from utils import TestCase

from codereview import models

class AccountTest(TestCase):
	def test_account_create(self):
		resp = self.client.get('/', follow=True)
		self.assertEquals(len(resp.redirect_chain), 2)
		self.assertEquals([302, 302], [it[1] for it in resp.redirect_chain])
		self.assertEquals(resp.content, 0)