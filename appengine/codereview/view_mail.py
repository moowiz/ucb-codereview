from view_decorators import post_required
from view_diff import _get_affected_files
from view_issue_draft import _get_draft_message, _get_draft_details
from view_utils import reverse, _encode_safely, InvalidIncomingEmailError, HttpTextResponse
from view_issue import show
from view_root import index

import settings as app_settings
import models
import library
import logging
import email.utils as _email_utils
import re
import datetime

from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.runtime import apiproxy_errors

from django.utils import encoding
from django.conf import settings as django_settings
import django.template
from django.shortcuts import render_to_response
from django.template import RequestContext

@post_required
def incoming_mail(request, recipients):
  """/_ah/mail/(.*)

  Handle incoming mail messages.

  The issue is not modified. No reviewers or CC's will be added or removed.
  """
  try:
    _process_incoming_mail(request.raw_post_data, recipients, request.semester)
  except InvalidIncomingEmailError, err:
    logging.debug(str(err))
  return HttpTextResponse('')


def _process_incoming_mail(raw_message, recipients, semester):
  """Process an incoming email message."""
  recipients = [x[1] for x in _email_utils.getaddresses([recipients])]

  incoming_msg = mail.InboundEmailMessage(raw_message)

  if 'X-Google-Appengine-App-Id' in incoming_msg.original:
    raise InvalidIncomingEmailError('Mail sent by App Engine')

  subject = incoming_msg.subject or ''
  match = re.search(r'\(issue *(?P<id>\d+)\)$', subject)
  if match is None:
    raise InvalidIncomingEmailError('No issue id found: %s', subject)
  issue_id = int(match.groupdict()['id'])
  issue = models.Issue.get_by_id(issue_id, semester)
  if issue is None:
    raise InvalidIncomingEmailError('Unknown issue ID: %d' % issue_id)
  sender = _email_utils.parseaddr(incoming_msg.sender)[1]

  body = None
  for _, payload in incoming_msg.bodies('text/plain'):
    # FIXME(andi): Remove this when issue 2383 is fixed.
    # 8bit encoding results in UnknownEncodingError, see
    # http://code.google.com/p/googleappengine/issues/detail?id=2383
    # As a workaround we try to decode the payload ourselves.
    if payload.encoding == '8bit' and payload.charset:
      body = payload.payload.decode(payload.charset)
    else:
      body = payload.decode()
    break
  if body is None or not body.strip():
    raise InvalidIncomingEmailError('Ignoring empty message.')
  elif len(body) > django_settings.RIETVELD_INCOMING_MAIL_MAX_SIZE:
    # see issue325, truncate huge bodies
    trunc_msg = '... (message truncated)'
    end = django_settings.RIETVELD_INCOMING_MAIL_MAX_SIZE - len(trunc_msg)
    body = body[:end]
    body += trunc_msg

  # If the subject is long, this might come wrapped into more than one line.
  subject = ' '.join([x.strip() for x in subject.splitlines()])
  msg = models.Message(issue=issue, parent=issue,
                       subject=subject,
                       sender=db.Email(sender),
                       recipients=[db.Email(x) for x in recipients],
                       date=datetime.datetime.now(),
                       text=db.Text(body),
                       draft=False)
  msg.put()

  # Add sender to reviewers if needed.
  all_emails = [str(x).lower()
                for x in issue.reviewers]
  if sender.lower() not in all_emails:
    query = models.Account.all().ancestor(issue.parent().key()).filter('lower_email =', sender.lower())
    account = query.get()
    if account is not None:
      issue.reviewers.append(account.email)  # e.g. account.email is CamelCase
    else:
      issue.reviewers.append(db.Email(sender))
    issue.put()

def _make_message(request, issue, message, comments=None, send_mail=False,
                  draft=None, in_reply_to=None):
  """Helper to create a Message instance and optionally send an email."""
  attach_patch = request.POST.get("attach_patch") == "yes"
  template, context = _get_mail_template(request, issue, full_diff=attach_patch)
  # Decide who should receive mail
  my_email = db.Email(request.user.email())
  to = issue.owners[:] + issue.reviewers[:]
  reply_to = to[:]
  reply_to.insert(0, app_settings.RIETVELD_INCOMING_MAIL_ADDRESS)
  if my_email in to and len(to) > 1:  # send_mail() wants a non-empty to list
    to.remove(my_email)
  reply_to = [db.Email(email) for email in reply_to]
  subject = '%s (issue %d)' % (issue.subject, issue.key().id())
  patch = None
  if attach_patch:
    subject = 'PATCH: ' + subject
    if 'patch' in context:
      patch = context['patch']
      del context['patch']
  if issue.message_set.count(1) > 0:
    subject = 'Re: ' + subject
  if comments:
    details = _get_draft_details(request, comments)
  else:
    details = ''
  message = message.replace('\r\n', '\n')
  text = ((message.strip() + '\n\n' + details.strip())).strip()
  if draft is None:
    msg = models.Message(issue=issue,
                         subject=subject,
                         sender=my_email,
                         recipients=reply_to,
                         text=db.Text(text),
                         parent=issue)
  else:
    msg = draft
    msg.subject = subject
    msg.recipients = reply_to
    msg.text = db.Text(text)
    msg.draft = False
    msg.date = datetime.datetime.now()

  if in_reply_to:
    try:
      msg.in_reply_to = models.Message.get(in_reply_to)
      replied_issue_id = msg.in_reply_to.issue.key().id()
      issue_id = issue.key().id()
      if replied_issue_id != issue_id:
        logging.warn('In-reply-to Message is for a different issue: '
                     '%s instead of %s', replied_issue_id, issue_id)
        msg.in_reply_to = None
    except (db.KindError, db.BadKeyError):
      logging.warn('Invalid in-reply-to Message or key given: %s', in_reply_to)

  send_mail = request.is_staff
  if send_mail:
    # Limit the list of files in the email to approximately 200
    if 'files' in context and len(context['files']) > 210:
      num_trimmed = len(context['files']) - 200
      del context['files'][200:]
      context['files'].append('[[ %d additional files ]]' % num_trimmed)
    url = request.build_absolute_uri(reverse(request, show, args=[issue.key().id()]))
    reviewer_nicknames = ', '.join(library.get_nickname(rev_temp, never_me=True, curr_acc=models.Account.current_user_account)
                                   for rev_temp in issue.reviewers)
    my_nickname = library.get_nickname(request.user, never_me=True, curr_acc=models.Account.current_user_account)
    reply_to = ', '.join(reply_to)
    home = request.build_absolute_uri(reverse(request, index))
    context.update({'reviewer_nicknames': reviewer_nicknames,
                    'my_nickname': my_nickname, 'url': url,
                    'message': message, 'details': details,
                    'home': home,
                    })
    for key, value in context.iteritems():
      if isinstance(value, str):
        try:
          encoding.force_unicode(value)
        except UnicodeDecodeError:
          logging.error('Key %s is not valid unicode. value: %r' % (key, value))
          # The content failed to be decoded as utf-8. Enforce it as ASCII.
          context[key] = value.decode('ascii', 'replace')
    body = django.template.loader.render_to_string(
      template, context, context_instance=RequestContext(request))
    logging.info('Mail: to=%s', ', '.join(to))
    send_args = {'sender': my_email,
                 'to': [_encode_safely(address) for address in to],
                 'subject': _encode_safely(subject),
                 'body': _encode_safely(body),
                 'reply_to': _encode_safely(reply_to)}
    if patch:
      send_args['attachments'] = [('issue_%s_patch.diff' % issue.key().id(),
                                   patch)]

    attempts = 0
    while True:
      try:
        mail.send_mail(**send_args)
        break
      except apiproxy_errors.DeadlineExceededError:
        # apiproxy_errors.DeadlineExceededError is raised when the
        # deadline of an API call is reached (e.g. for mail it's
        # something about 5 seconds). It's not the same as the lethal
        # runtime.DeadlineExeededError.
        attempts += 1
        if attempts >= 3:
          raise
    if attempts:
      logging.warning("Retried sending email %s times", attempts)

  return msg

def _get_mail_template(request, issue, full_diff=False):
  """Helper to return the template and context for an email.

  If this is the first email sent by the owner, a template that lists the
  reviewers, description and files is used.
  """
  context = {}
  template = 'mails/comment.txt'
  if db.GqlQuery('SELECT * FROM Message WHERE ANCESTOR IS :1 AND sender = :2',
                issue, db.Email(request.user.email())).count(1) == 0:
    template = 'mails/review.txt'
    files, patch = _get_affected_files(issue, full_diff)
    context.update({'files': files, 'patch': patch, })
  return template, context
