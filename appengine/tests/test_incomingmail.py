from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.appengine.api.users import User

from utils import TestCase

from codereview import models, views


class TestIncomingMail(TestCase):

  def url(self, url):
    return '/%s%s' % (self.issue.parent().name, url)

  def setUp(self):
    super(TestIncomingMail, self).setUp()
    self.login('foo@example.com')
    self.user = User('foo@example.com')
    self.semester = models.Semester(key_name='<sp14>', name='sp14')
    self.semester.put()

    self.issue = models.Issue(subject=models.VALID_SUBJECTS[0], parent=self.semester)
    self.issue.put()
    self.issue2 = models.Issue(subject=models.VALID_SUBJECTS[1], parent=self.semester)
    self.issue2.put()
    self.logout()

  def test_incoming_mail(self):
    msg = Message()
    msg['To'] = test_to = 'reply@example.com'
    msg['From'] = test_from = 'sender@example.com'
    msg['Subject'] = test_subj = 'subject (issue%s)' % self.issue.key().id()
    msg.set_payload('body')
    response = self.client.post(self.url('/_ah/mail/reply@example.com'),
                                msg.as_string(), content_type='text/plain')
    self.assertEqual(response.content,  '')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(models.Message.all().ancestor(self.issue).count(), 1)
    self.assertEqual(models.Message.all().ancestor(self.issue2).count(), 0)
    msg = models.Message.all().ancestor(self.issue).get()
    self.assertEqual(msg.text, 'body')
    self.assertEqual(msg.subject, test_subj)
    self.assertEqual(msg.sender, test_from)
    self.assertEqual(msg.recipients, [test_to])
    self.assert_(msg.date is not None)
    self.assertEqual(msg.draft, False)

  def test_incoming_mail_invalid_subject(self):
    msg = Message()
    msg['To'] = 'reply@example.com'
    msg['From'] = 'sender@example.com'
    msg['Subject'] = 'invalid'
    msg.set_payload('body')
    response = self.client.post(self.url('/_ah/mail/reply@example.com'),
                                msg, content_type='text/plain')
    self.assertEqual(response.status_code, 200)
    self.assertEqual(models.Message.all().ancestor(self.issue).count(), 0)

  def test_unknown_issue(self):
    msg = Message()
    msg['From'] = 'sender@example.com'
    msg['Subject'] = 'subject (issue99999)'
    msg.set_payload('body')
    self.assertRaises(views.InvalidIncomingEmailError,
                      views._process_incoming_mail, msg.as_string(),
                      'reply@example.com', self.semester)

  def test_empty_message(self):
    msg = Message()
    msg['From'] = 'sender@example.com'
    msg['Subject'] = 'subject (issue%s)\r\n\r\n' % self.issue.key().id()
    self.assertRaises(views.InvalidIncomingEmailError,
                      views._process_incoming_mail, msg.as_string(),
                      'reply@example.com', self.semester)

  def test_senders_becomes_reviewer(self):
    msg = Message()
    msg['From'] ='sender@example.com'
    msg['Subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg.set_payload('body')
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    issue = models.Issue.get_by_id(self.issue.key().id(), self.semester)  # re-fetch issue
    self.assertEqual(issue.reviewers, ['sender@example.com'])
    issue.reviewers = []
    issue.put()
    # try again with sender that has an account
    # we do this to handle CamelCase emails correctly
    models.Account.get_account_for_user(User('sender@example.com'))
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    issue = models.Issue.get_by_id(self.issue.key().id(), self.semester)
    self.assertEqual(issue.reviewers, ['sender@example.com'])

  def test_long_subjects(self):
    # multi-line subjects should be collapsed into a single line
    msg = Message()
    msg['Subject'] = ('foo '*30)+' (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    msg.set_payload('body')
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    imsg = models.Message.all().ancestor(self.issue).get()
    self.assertEqual(len(imsg.subject.splitlines()), 1)

  def test_multipart(self):
    # Text first
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    msg.attach(MIMEText('body', 'plain'))
    msg.attach(MIMEText('ignore', 'html'))
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    imsg = models.Message.all().ancestor(self.issue).get()
    self.assertEqual(imsg.text, 'body')
    imsg.delete()
    # HTML first
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    msg.attach(MIMEText('ignore', 'html'))
    msg.attach(MIMEText('body', 'plain'))
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    imsg = models.Message.all().ancestor(self.issue).get()
    self.assertEqual(imsg.text, 'body')
    imsg.delete()
    # no text at all
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    msg.attach(MIMEText('ignore', 'html'))
    self.assertRaises(views.InvalidIncomingEmailError,
                      views._process_incoming_mail, msg.as_string(),
                      'reply@example.com', self.semester)

  def test_mails_from_appengine(self):  # bounces
    msg = Message()
    msg['Subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    msg['X-Google-Appengine-App-Id'] = 'foo'
    self.assertRaises(views.InvalidIncomingEmailError,
                      views._process_incoming_mail, msg.as_string(),
                      'reply@exampe.com', self.semester)

  def test_huge_body_is_truncated(self):  # see issue325
    msg = Message()
    msg['subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    msg.set_payload('1' * 600 * 1024)
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    imsg = models.Message.all().ancestor(self.issue).get()
    self.assertEqual(len(imsg.text), 500 * 1024)
    self.assert_(imsg.text.endswith('... (message truncated)'))

  def test_charset(self):
    # make sure that incoming mails with non-ascii chars are handled correctly
    # see related http://code.google.com/p/googleappengine/issues/detail?id=2326
    jtxt = '\x1b$B%O%m!<%o!<%k%I!*\x1b(B'
    jcode = 'iso-2022-jp'
    msg = Message()
    msg.set_payload(jtxt, jcode)
    msg['Subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    imsg = models.Message.all().ancestor(self.issue).get()
    self.assertEqual(imsg.text.encode(jcode), jtxt)

  def test_encoding(self):
    # make sure that incoming mails with 8bit encoding are handled correctly.
    # see realted http://code.google.com/p/googleappengine/issues/detail?id=2383
    jtxt = '\x1b$B%O%m!<%o!<%k%I!*\x1b(B'
    jcode = 'iso-2022-jp'
    msg = Message()
    msg.set_payload(jtxt, jcode)
    msg['Subject'] = 'subject (issue%s)' % self.issue.key().id()
    msg['From'] = 'sender@example.com'
    del msg['Content-Transfer-Encoding']  # replace 7bit encoding
    msg['Content-Transfer-Encoding'] = '8bit'
    views._process_incoming_mail(msg.as_string(), 'reply@example.com', self.semester)
    imsg = models.Message.all().ancestor(self.issue).get()
    self.assertEqual(imsg.text.encode(jcode), jtxt)
