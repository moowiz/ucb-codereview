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

"""Tests for view functions and helpers."""

import os
from string import Template

from django.http import HttpRequest

from google.appengine.api.users import User
from google.appengine.ext import db
from google.appengine.ext import testbed

from utils import TestCase, load_file

from codereview import models, view_issue_draft
from codereview import engine  # engine must be imported after models :(


class MockRequest(HttpRequest):
    """Mock request class for testing."""

    def __init__(self, user=None, issue=None):
        super(MockRequest, self).__init__()
        self.META['HTTP_HOST'] = 'testserver'
        self.user = user
        self.issue = issue
        self.semester = models.Semester.get_by_key_name('<fa13>') # Chosen arbitrarily

class TestViewBase(TestCase):
    def setUp(self):
        super(TestViewBase, self).setUp()
        self.semester = models.Semester.get_or_insert('<fa13>', name='fa13')

        self.ta_acc = self.make_ta(self.semester)
        self.student_acc = self.make_student(self.semester)
        self.other_acc = self.make_student(self.semester)

        self.issue = self.make_issue(owners=[self.student_acc.email], reviewers=[self.other_acc.email])

        self.ps = models.PatchSet(parent=self.issue, issue=self.issue)
        self.ps.data = load_file('ps1.diff')
        self.ps.save()
        self.patches = engine.ParsePatchSet(self.ps)
        db.put(self.patches)

        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)
        self.user_stub = self.testbed.get_stub(testbed.USER_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

class TestStudentUserViewing(TestViewBase):
    def test_basic(self):
        self.login(self.student_acc.email)

        resp = self.client.get('/%s/mine' % self.semester.name)
        temp = Template("""
<tr name="issue">
  <td class="first" width="14"><img src="/static/closedtriangle.gif"
    style="visibility: hidden;" width="12" height="9" /></td>
  <td width="34" align="left" style="white-space: nowrap"><span id="issue-star-$issueNum">
      <a href="javascript:M_addIssueStar($issueNum)">
    <img src="/static/star-dark.gif" width="15" height="15" border="0"></a>
</span>
    </td>
  <td align="right"><div class="subject"><a class="noul"
         href="/$semester/$issueNum/">$issueNum</a>
     </div>
  </td>
  <td>
    <div class="subject">
      <a class="noul" href="/$semester/$issueNum/"
      id="issue-title-$issueNum">$issueSubject</a>
    </div>
  </td>
  <td><div class="users">
          me
  </div></td>
  <td><div class="users">
          Anonymous
  </div></td>
  <td>
          Not graded yet
  </td>
  <td align="center"></td>
  <td align="center"></td>
  <td align="center"><b></b></td>
  <td align="center">$numSubmissions</td>
  <td class="last">
  <div class="date">
  0 minutes
  </div>
  </td>
  </tr>""")
        self.assertContains(resp, temp.substitute(semester = self.semester.name, issueNum = self.issue.key().id(),
                                                    numSubmissions = models.PatchSet.all().ancestor(self.issue).count(),
                                                    issueSubject=self.issue.subject, email=self.student_acc.email), html=True)

    def test_settings(self):
        self.login(self.ta_acc.email)
        resp = self.client.get('/%s/user/%s/settings' % (self.semester.name, self.student_acc.email))
        self.assertContains(resp, "Role:")
        self.logout()

        self.login(self.student_acc.email)
        resp = self.client.get('/%s/user/%s/settings' % (self.semester.name, self.student_acc.email))
        self.assertNotContains(resp, "Role:")
        self.logout()

class TestPublish(TestViewBase):
    """Test publish functions."""
    def setUp(self):
        super(TestPublish, self).setUp()
        self.login(self.student_acc.email)

    def count_num(self, cls):
        return cls.all().ancestor(self.issue.key()).count()

    def test_correct_simple_publish(self):
        self.login(self.ta_acc.email)
        data = {
            'reviewers': self.student_acc.email + ', billy@example.com',
            'comp_score': '3',
            'bug_submit': 'False',
            'send_mail': 'True',
            'message': 'Hi there, this is a test message. Please ignore',
            'message_only': '',
            'in_reply_to': '',
            'xsrf_token': self.ta_acc.get_xsrf_token(),
        }
        url = '/%s/%s/' % (self.semester.name, self.issue.key().id())
        resp = self.client.post(url + 'publish', data=data, follow=True)

        self.assertRedirects(resp, url)
        self.assertContains(resp, data['message'])

        self.assertEqual(self.count_num(models.Message), 1) # Only sent 1 message
        self.assertEqual(self.count_num(models.Comment), 0)
        messages = self.mail_stub.get_sent_messages()
        self.assertEqual(1, len(messages))
        self.logout()

    def test_correct_complex_publish(self):
        self.login(self.ta_acc.email)

        messages_before = self.count_num(models.Message)
        comments_before = self.count_num(models.Comment)

        data = {
            'reviewers': 'foo@example.com, billy@example.com',
            'comp_score': '3',
            'bug_submit': 'False',
            'send_mail': 'True',
            'message': 'Hi there, this is a test message. Please ignore',
            'message_only': '',
            'in_reply_to': '',
            'xsrf_token': self.ta_acc.get_xsrf_token(),
        }
        url = '/%s/%s/' % (self.semester.name, self.issue.key().id())
        resp = self.client.post(url + 'publish', data=data, follow=True)

        self.assertContains(resp, data['message'])
        self.assertRedirects(resp, url)

        self.assertEqual(self.count_num(models.Message) - 1, messages_before) # Only sent 1 message
        self.assertEqual(self.count_num(models.Comment), comments_before)
        messages = self.mail_stub.get_sent_messages()
        self.assertEqual(1, len(messages))

        self.logout()

    def test_draft_details_no_base_file(self):
        self.login(self.student_acc.email)

        request = MockRequest(self.student_acc.user, issue=self.issue)
        # add a comment and render
        cmt1 = models.Comment(patch=self.patches[0], parent=self.patches[0])
        cmt1.text = 'test comment'
        cmt1.lineno = 1
        cmt1.left = False
        cmt1.draft = True
        cmt1.author = self.student_acc.user
        cmt1.save()
        # Add a second comment
        cmt2 = models.Comment(patch=self.patches[1], parent=self.patches[1])
        cmt2.text = 'test comment 2'
        cmt2.lineno = 2
        cmt2.left = False
        cmt2.draft = True
        cmt2.author = self.student_acc.user
        cmt2.save()
        # Add fake content
        content1 = models.Content(text="foo\nbar\nbaz\nline\n")
        content1.put()
        content2 = models.Content(text="foo\nbar\nbaz\nline\n")
        content2.put()
        cmt1.patch.content = content1
        cmt1.patch.put()
        cmt2.patch.content = content2
        cmt2.patch.put()
        # Mock get content calls. The first fails with an FetchError,
        # the second succeeds (see issue384).
        def raise_err():
            raise models.FetchError()
        cmt1.patch.get_content = raise_err
        cmt2.patch.get_patched_content = lambda: content2
        tbd, comments = view_issue_draft._get_draft_comments(request, self.issue)
        self.assertEqual(len(comments), 2)
        # Try to render draft details using the patched Comment
        # instances from here.
        view_issue_draft._get_draft_details(request, [cmt1, cmt2])

        self.logout()
