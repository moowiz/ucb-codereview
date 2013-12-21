from google.appengine.ext import db

from view_mail import _make_message

import models
import engine
import utils

class EmptyPatchSet(Exception):
  """Exception used inside _make_new() to break out of the transaction."""

def _make_new(request, form):
  """Creates new issue and fill relevant fields from given form data.

  Sends notification about created issue (if requested with send_mail param).

  Returns (Issue, PatchSet) or (None, None).
  """
  if not form.is_valid():
    return (None, None)

  data_url = _get_data_url(form)
  if data_url is None:
    return (None, None)
  data, url, separate_patches = data_url

  owners = _get_emails(form, 'owners')
  if not form.is_valid() or owners is None:
    return (None, None)

  def txn():
    issue = models.Issue(subject=form.cleaned_data['subject'],
                         description=form.cleaned_data['description'],
                         owners=owners,
                         n_comments=0)

    issue.put()

    patchset = models.PatchSet(issue=issue, data=data, url=url, parent=issue)
    patchset.put()

    if not separate_patches:
      patches = engine.ParsePatchSet(patchset)
      if not patches:
        raise EmptyPatchSet  # Abort the transaction
      db.put(patches)
    return issue, patchset

  try:
    xg_on = db.create_transaction_options(xg=True)
    issue, patchset = db.run_in_transaction_options(xg_on, txn)
  except EmptyPatchSet:
    errkey = url and 'url' or 'data'
    form.errors[errkey] = ['Patch set contains no recognizable patches']
    return (None, None)

  if form.cleaned_data.get('send_mail'):
    msg = _make_message(request, issue, '', '', True)
    msg.put()
  return (issue, patchset)


def _get_data_url(form):
  """Helper for _make_new() above and add() below.

  Args:
    form: Django form object.

  Returns:
    3-tuple (data, url, separate_patches).
      data: the diff content, if available.
      url: the url of the diff, if given.
      separate_patches: True iff the patches will be uploaded separately for
        each file.

  """
  cleaned_data = form.cleaned_data

  data = cleaned_data['data']
  url = cleaned_data.get('url')
  separate_patches = cleaned_data.get('separate_patches')
  if not (data or url or separate_patches):
    form.errors['data'] = ['You must specify a URL or upload a file (< 1 MB).']
    return None
  if data and url:
    form.errors['data'] = ['You must specify either a URL or upload a file '
                           'but not both.']
    return None
  if separate_patches and (data or url):
    form.errors['data'] = ['If the patches will be uploaded separately later, '
                           'you can\'t send some data or a url.']
    return None

  if data is not None:
    data = db.Blob(utils.unify_linebreaks(data.read()))
    url = None
  elif url:
    try:
      fetch_result = urlfetch.fetch(url)
    except Exception, err:
      form.errors['url'] = [str(err)]
      return None
    if fetch_result.status_code != 200:
      form.errors['url'] = ['HTTP status code %s' % fetch_result.status_code]
      return None
    data = db.Blob(utils.unify_linebreaks(fetch_result.content))

  return data, url, separate_patches

def _get_emails(form, label):
  """Helper to return the list of reviewers, or None for error."""
  raw_emails = form.cleaned_data.get(label)
  if raw_emails:
    return _get_emails_from_raw(raw_emails.split(','), form=form, label=label)
  return []

def _get_emails_from_raw(raw_emails, form=None, label=None):
  emails = []
  for email in raw_emails:
    email = email.strip()
    if email:
      try:
        if '@' not in email:
          account = models.Account.get_account_for_nickname(email)
          if account is None:
            raise db.BadValueError('Unknown user: %s' % email)
          db_email = db.Email(account.user.email().lower())
        elif email.count('@') != 1:
          raise db.BadValueError('Invalid email address: %s' % email)
        else:
          _, tail = email.split('@')
          if '.' not in tail:
            raise db.BadValueError('Invalid email address: %s' % email)
          db_email = db.Email(email.lower())
      except db.BadValueError, err:
        if form:
          form.errors[label] = [unicode(err)]
        return None
      if db_email not in emails:
        emails.append(db_email)
  return emails
