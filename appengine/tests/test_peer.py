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

"""Tests for peer code review features"""

import os

from django.http import HttpRequest

from google.appengine.api.users import User
from google.appengine.ext import db
from google.appengine.ext import testbed

from utils import TestCase, load_file

from codereview import views

class TestPeer(TestCase):
    def setUp(self):
        super(TestPeer, self).setUp()
        self.ta_acc = self.make_ta(self.semester)
        self.stus = self.make_students(self.semester)

        self.issues = self.make_issues(len(self.stus), owners_lst=[[x.email] for x in self.stus])

        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)
        self.user_stub = self.testbed.get_stub(testbed.USER_SERVICE_NAME)

        self._old_stus = views.CODE_REVIEW_STUDENTS
        views.CODE_REVIEW_STUDENTS = [acc.email for acc in self.stus]

    def tearDown(self):
        self.testbed.deactivate()
        views.CODE_REVIEW_STUDENTS = self._old_stus

    def test_algorithm(self):
        return #We don't use this anymore, at least for now
        views.assign_peer_reviewers(self.semester, self.issues[0].subject)
        self.issues = db.get(iss.key() for iss in self.issues)
        for issue in self.issues:
            self.assertEqual(len(issue.owners), 1, "Bad number of owners")
            self.assertEqual(len(issue.reviewers), 2, "Bad number of reviewers")
            self.assertEqual(len(set(issue.reviewers + issue.owners)), 3,
                "Duplicates detected in issue {}!\nreviewers: {} owners: {}".format(issue.key().id(), issue.reviewers, issue.owners))
