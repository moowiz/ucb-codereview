# Copyright 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test utils."""

import os
import random
import string

from google.appengine.ext import testbed
from google.appengine.ext import db
from google.appengine.api.users import User

from django.test import TestCase as _TestCase

from codereview import models

FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')

def rand_nick(length=10):
  return ''.join(random.choice(string.letters) for x in range(length))

class TestCase(_TestCase):
  """Customized Django TestCase.

  This class disables the setup of Django features that are not
  available on App Engine (e.g. fixture loading). And it initializes
  the Testbed class provided by the App Engine SDK.
  """

  EMAIL_SUFF = '@example.com'

  def _fixture_setup(self):  # defined in django.test.TestCase
    pass

  def _fixture_teardown(self):  # defined in django.test.TestCase
    pass

  def setUp(self):
    super(TestCase, self).setUp()
    self.EMAIL_SUFF = '@example.com'
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_user_stub()
    self.testbed.init_logservice_stub()
    self.testbed.init_memcache_stub()

    self.semester = models.Semester.get_or_insert('<sp14>', name='sp14')

  def tearDown(self):
    self.testbed.deactivate()
    super(TestCase, self).tearDown()

  def login(self, email):
    """Logs in a user identified by email."""
    os.environ['USER_EMAIL'] = email

  def logout(self):
    """Logs the user out."""
    os.environ['USER_EMAIL'] = ''

  @classmethod
  def make_email(cls, nick):
    return nick + cls.EMAIL_SUFF

  @classmethod
  def make_ta(cls, semester):
    ta = User(cls.make_email('ta'))
    ta_acc = models.Account.get_account_for_user(ta, semester)
    ta_acc.role = models.ROLE_MAPPING['ta']
    ta_acc.put()

    return ta_acc

  @classmethod
  def make_tas(cls, semester, num=5):
    return [cls.make_ta(semester) for _ in range(num)]

  @classmethod
  def make_student(cls, semester):
    stu = User(cls.make_email(rand_nick()))
    stu_acc = models.Account.get_account_for_user(stu)
    stu_acc.role = models.ROLE_MAPPING['student']
    stu_acc.put()

    return stu_acc

  @classmethod
  def make_students(cls, semester, num=20):
    return [cls.make_student(semester) for _ in range(num)]

  def make_issue(self, semester=None, subject=None, owners=[], reviewers=[]):
    if not subject:
      subject = models.VALID_SUBJECTS[0]
    if not semester:
      semester = self.semester

    owners = [(db.Email(x) if type(x) is str else x) for x in owners]
    reviewers = [(db.Email(x) if type(x) is str else x) for x in reviewers]
    issue = models.Issue(subject=subject, owners=owners, reviewers=reviewers, parent=semester)
    issue.put()

    return issue

  def make_issues(self, num, semester=None, subjects=None, owners_lst=None, reviewers_lst=None):
    if not semester:
      semester = self.semester

    if not subjects:
      subjects = [models.VALID_SUBJECTS[0] for x in range(num)]

    rval = []
    for i in range(num):
      rval.append(self.make_issue(semester, subjects[i],
          (owners_lst[i] if owners_lst else []), (reviewers_lst[i] if reviewers_lst else [])))

    return rval

def load_file(fname):
  """Read file and return it's content."""
  with open(os.path.join(FILES_DIR, fname)) as f:
    return f.read()
