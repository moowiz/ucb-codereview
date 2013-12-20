

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