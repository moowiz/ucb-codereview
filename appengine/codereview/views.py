# Copyright 2008 Google Inc.
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

"""Views for Rietveld."""

import binascii
import datetime
import email.utils as _email_utils
import collections
import logging
import hashlib
import mimetypes
import os
import random
import re
import urllib
import json
import settings as app_settings
from cStringIO import StringIO
from xml.etree import ElementTree

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.api import xmpp
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.runtime import DeadlineExceededError
from google.appengine.runtime import apiproxy_errors

# Import settings as django_settings to avoid name conflict with settings().
from django.conf import settings as django_settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
import django.template
from django.template import RequestContext
from django.utils import encoding
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse as _reverse
from django.views.decorators.http import last_modified

from codereview import engine
from codereview import library
from codereview import models
from codereview import patching
from codereview import utils
from codereview import forms
from codereview.exceptions import FetchError

# Add our own custom template tags library.
django.template.add_to_builtins('codereview.library')

from view_issue import *
from view_mail import *
from view_root import *
from view_taskQ import *
from view_users import *


@login_required
def starred(request):
  """/starred - Show a list of issues starred by the current user."""
  stars = models.Account.current_user_account.stars
  if not stars:
    issues = []
  else:
    issues = [issue for issue in models.Issue.get_by_id(stars, request.semester)
                    if issue is not None
                    and _can_view_issue(request, issue)]
    _load_users_for_issues(issues)
    _optimize_draft_counts(issues)
  return respond(request, 'starred.html', {'issues': issues})

def _load_users_for_issues(issues):
  """Load all user links for a list of issues in one go."""
  if not issues:
    return

  user_dict = {}
  for i in issues:
    for e in i.reviewers:
      # keeping a count lets you track total vs. distinct if you want
      user_dict[e] = user_dict.setdefault(e, 0) + 1

@login_required
@xsrf_required
def new(request):
  """/new - Upload a new patch set.

  GET shows a blank form, POST processes it.
  """
  if request.method != 'POST':
    form = forms.NewForm()
    return respond(request, 'new.html', {'form': form})

  form = forms.NewForm(request.POST, request.FILES)
  issue, _ = _make_new(request, form)
  if issue is None:
    return respond(request, 'new.html', {'form': form})
  else:
    return HttpResponseRedirect(reverse(request, show, args=[issue.key().id()]))

@post_required
@issue_required
@xsrf_required
def add(request):
  """/<issue>/add - Add a new PatchSet to an existing Issue."""
  issue = request.issue
  form = forms.AddForm(request.POST, request.FILES)
  if not _add_patchset_from_form(request, issue, form):
    return show(request, issue.key().id(), form)
  return HttpResponseRedirect(reverse(request, show, args=[issue.key().id()]))


def _add_patchset_from_form(request, issue, form, message_key='message',
                            emails_add_only=False):
  """Helper for add() and upload()."""
  # TODO(guido): use a transaction like in _make_new(); may be share more code?
  if form.is_valid():
    data_url = _get_data_url(form)
  if not form.is_valid():
    return None
  data, url, separate_patches = data_url
  message = form.cleaned_data[message_key]
  patchset = models.PatchSet(issue=issue, message=message, data=data, url=url,
                             parent=issue)
  patchset.put()

  if not separate_patches:
    patches = engine.ParsePatchSet(patchset)
    if not patches:
      patchset.delete()
      errkey = url and 'url' or 'data'
      form.errors[errkey] = ['Patch set contains no recognizable patches']
      return None
    db.put(patches)

  if form.cleaned_data.get('send_mail'):
    msg = _make_message(request, issue, message, '', True)
    msg.put()
  return patchset


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


@handle_year
def _calculate_delta(patch, patchset_id, patchsets):
  """Calculates which files in earlier patchsets this file differs from.

  Args:
    patch: The file to compare.
    patchset_id: The file's patchset's key id.
    patchsets: A list of existing patchsets.

  Returns:
    A list of patchset ids.
  """
  delta = []
  if patch.no_base_file:
    return delta
  for other in patchsets:
    if patchset_id == other.key().id():
      break
    if not hasattr(other, 'parsed_patches'):
      other.parsed_patches = None  # cache variable for already parsed patches
    if other.data or other.parsed_patches:
      # Loading all the Patch entities in every PatchSet takes too long
      # (DeadLineExceeded) and consumes a lot of memory (MemoryError) so instead
      # just parse the patchset's data.  Note we can only do this if the
      # patchset was small enough to fit in the data property.
      if other.parsed_patches is None:
        # PatchSet.data is stored as db.Blob (str). Try to convert it
        # to unicode so that Python doesn't need to do this conversion
        # when comparing text and patch.text, which is db.Text
        # (unicode).
        try:
          other.parsed_patches = engine.SplitPatch(other.data.decode('utf-8'))
        except UnicodeDecodeError:  # Fallback to str - unicode comparison.
          other.parsed_patches = engine.SplitPatch(other.data)
        other.data = None  # Reduce memory usage.
      for filename, text in other.parsed_patches:
        if filename == patch.filename:
          if text != patch.text:
            delta.append(other.key().id())
          break
      else:
        # We could not find the file in the previous patchset. It must
        # be new wrt that patchset.
        delta.append(other.key().id())
    else:
      # other (patchset) is too big to hold all the patches inside itself, so
      # we need to go to the datastore.  Use the index to see if there's a
      # patch against our current file in other.
      query = models.Patch.all()
      query.filter("filename =", patch.filename)
      query.filter("patchset =", other.key())
      other_patches = query.fetch(100)
      if other_patches and len(other_patches) > 1:
        logging.info("Got %s patches with the same filename for a patchset",
                     len(other_patches))
      for op in other_patches:
        if op.text != patch.text:
          delta.append(other.key().id())
          break
      else:
        # We could not find the file in the previous patchset. It must
        # be new wrt that patchset.
        delta.append(other.key().id())

  return delta


def _get_patchset_info(request, patchset_id):
  """ Returns a list of patchsets for the issue.

  Args:
    request: Django Request object.
    patchset_id: The id of the patchset that the caller is interested in.  This
      is the one that we generate delta links to if they're not available.  We
      can't generate for all patchsets because it would take too long on issues
      with many patchsets.  Passing in None is equivalent to doing it for the
      last patchset.

  Returns:
    A 3-tuple of (issue, patchsets, HttpResponse).
    If HttpResponse is not None, further processing should stop and it should be
    returned.
  """
  issue = request.issue
  patchsets = list(issue.patchset_set.order('created'))
  response = None
  if not patchset_id and patchsets:
    patchset_id = patchsets[-1].key().id()

  if request.user:
    drafts = list(models.Comment.gql('WHERE ANCESTOR IS :1 AND draft = TRUE'
                                     '  AND author = :2',
                                     issue, request.user))
  else:
    drafts = []
  comments = list(models.Comment.gql('WHERE ANCESTOR IS :1 AND draft = FALSE',
                                     issue))
  issue.draft_count = len(drafts)
  for c in drafts:
    c.ps_key = c.patch.patchset.key()
  patchset_id_mapping = {}  # Maps from patchset id to its ordering number.
  for patchset in patchsets:
    patchset_id_mapping[patchset.key().id()] = len(patchset_id_mapping) + 1
    patchset.n_drafts = sum(c.ps_key == patchset.key() for c in drafts)
    patchset.patches = None
    patchset.parsed_patches = None
    if patchset_id == patchset.key().id():
      patchset.patches = list(patchset.patch_set.order('filename'))
      try:
        attempt = _clean_int(request.GET.get('attempt'), 0, 0)
        if attempt < 0:
          response = HttpTextResponse('Invalid parameter', status=404)
          break
        for patch in patchset.patches:
          pkey = patch.key()
          patch._num_comments = sum(c.parent_key() == pkey for c in comments)
          patch._num_drafts = sum(c.parent_key() == pkey for c in drafts)
          if not patch.delta_calculated:
            if attempt > 2:
              # Too many patchsets or files and we're not able to generate the
              # delta links.  Instead of giving a 500, try to render the page
              # without them.
              patch.delta = []
            else:
              # Compare each patch to the same file in earlier patchsets to see
              # if they differ, so that we can generate the delta patch urls.
              # We do this once and cache it after.  It's specifically not done
              # on upload because we're already doing too much processing there.
              # NOTE: this function will clear out patchset.data to reduce
              # memory so don't ever call patchset.put() after calling it.
              patch.delta = _calculate_delta(patch, patchset_id, patchsets)
              patch.delta_calculated = True
              # A multi-entity put would be quicker, but it fails when the
              # patches have content that is large.  App Engine throws
              # RequestTooLarge.  This way, although not as efficient, allows
              # multiple refreshes on an issue to get things done, as opposed to
              # an all-or-nothing approach.
              patch.put()
          # Reduce memory usage: if this patchset has lots of added/removed
          # files (i.e. > 100) then we'll get MemoryError when rendering the
          # response.  Each Patch entity is using a lot of memory if the files
          # are large, since it holds the entire contents.  Call num_chunks and
          # num_drafts first though since they depend on text.
          # These are 'active' properties and have side-effects when looked up.
          # pylint: disable=W0104
          patch.num_chunks
          patch.num_drafts
          patch.num_added
          patch.num_removed
          patch.text = None
          patch._lines = None
          patch.parsed_deltas = []
          for delta in patch.delta:
            patch.parsed_deltas.append([patchset_id_mapping[delta], delta])
      except DeadlineExceededError:
        logging.exception('DeadlineExceededError in _get_patchset_info')
        if attempt > 2:
          response = HttpTextResponse(
              'DeadlineExceededError - create a new issue.')
        else:
          response = HttpResponseRedirect('%s?attempt=%d' %
                                          (request.path, attempt + 1))
        break
  # Reduce memory usage (see above comment).
  for patchset in patchsets:
    patchset.parsed_patches = None
  return issue, patchsets, response


@login_required
@issue_required
def show(request, form=None):
  """/<issue> - Show an issue."""
  if not _can_view_issue(request, request.issue):
      return HttpTextResponse(
          'You cannot view this issue.', status=403)
  issue, patchsets, response = _get_patchset_info(request, None)
  if response:
    return response
  if not form:
    form = forms.AddForm(initial={'reviewers': ', '.join(issue.reviewers)})
  last_patchset = first_patch = None
  if patchsets:
    last_patchset = patchsets[-1]
    if last_patchset.patches:
      first_patch = last_patchset.patches[0]
  messages = []
  has_draft_message = False
  for msg in issue.message_set.order('date'):
    if not msg.draft:
      messages.append(msg)
    elif msg.draft and request.user and msg.sender == request.user.email():
      has_draft_message = True
  num_patchsets = len(patchsets)
  return respond(request, 'issue.html',
                 {'issue': issue, 'patchsets': patchsets,
                  'messages': messages, 'form': form,
                  'last_patchset': last_patchset,
                  'num_patchsets': num_patchsets,
                  'first_patch': first_patch,
                  'has_draft_message': has_draft_message,
                  })


@patchset_required
def patchset(request):
  """/patchset/<key> - Returns patchset information."""
  patchset = request.patchset
  issue, patchsets, response = _get_patchset_info(request, patchset.key().id())
  if response:
    return response
  for ps in patchsets:
    if ps.key().id() == patchset.key().id():
      patchset = ps
  return respond(request, 'patchset.html',
                 {'issue': issue,
                  'patchset': patchset,
                  'patchsets': patchsets,
                  })


@login_required
def account(request):
  """/account/?q=blah&limit=10 - Used for autocomplete."""
  def searchAccounts(property, domain, added, response):
    query = request.GET.get('q').lower()
    limit = _clean_int(request.GET.get('limit'), 10, 10, 100)

    accounts = models.Account.all().ancestor(request.semester)
    accounts.filter("lower_%s >= " % property, query)
    accounts.filter("lower_%s < " % property, query + u"\ufffd")
    accounts.order("lower_%s" % property)
    for account in accounts:
      if account.key() in added:
        continue
      if domain and not account.email.endswith(domain):
        continue
      if len(added) >= limit:
        break
      added.add(account.key())
      response += '%s\n' % (account.email)
    return added, response

  added = set()
  response = ''
  domain = os.environ['AUTH_DOMAIN']
  if domain != 'gmail.com':
    # 'gmail.com' is the value AUTH_DOMAIN is set to if the app is running
    # on appspot.com and shouldn't prioritize the custom domain.
    added, response = searchAccounts("email", domain, added, response)
    added, response = searchAccounts("nickname", domain, added, response)
  added, response = searchAccounts("nickname", "", added, response)
  added, response = searchAccounts("email", "", added, response)
  return HttpTextResponse(response)


@issue_required
@staff_required
def release(request):
    request.issue.bug_owner = None
    request.issue.put()
    return HttpResponseRedirect(reverse(request, show, args=[request.issue.key().id()]))

@issue_required
@staff_required
def claim(request):
    request.issue.bug_owner = request.user.email()
    request.issue.bug = True
    request.issue.put()
    return HttpResponseRedirect(reverse(request, show, args=[request.issue.key().id()]))

@post_required
@xsrf_required
def delete_patchset(request):
  """/<issue>/patch/<patchset>/delete - Delete a patchset.

  There is no way back.
  """
  issue = request.issue
  ps_delete = request.patchset
  ps_id = ps_delete.key().id()
  patchsets_after = issue.patchset_set.filter('created >', ps_delete.created)
  patches = []
  for patchset in patchsets_after:
    for patch in patchset.patch_set:
      if patch.delta_calculated:
        if ps_id in patch.delta:
          patches.append(patch)
  db.run_in_transaction(_patchset_delete, ps_delete, patches)
  return HttpResponseRedirect(reverse(request, show, args=[issue.key().id()]))


def _patchset_delete(ps_delete, patches):
  """Transactional helper for delete_patchset.

  Args:
    ps_delete: The patchset to be deleted.
    patches: Patches that have delta against patches of ps_delete.

  """
  patchset_id = ps_delete.key().id()
  tbp = []
  for patch in patches:
    patch.delta.remove(patchset_id)
    tbp.append(patch)
  if tbp:
    db.put(tbp)
  tbd = [ps_delete]
  for cls in [models.Patch, models.Comment]:
    tbd += cls.gql('WHERE ANCESTOR IS :1', ps_delete)
  db.delete(tbd)


@patchset_required
def download(request):
  """/download/<issue>_<patchset>.diff - Download a patch set."""
  if request.patchset.data is None:
    return HttpTextResponse(
        'Patch set (%s) is too large.' % request.patchset.key().id(),
        status=404)
  padding = ''
  user_agent = request.META.get('HTTP_USER_AGENT')
  if user_agent and 'MSIE' in user_agent:
    # Add 256+ bytes of padding to prevent XSS attacks on Internet Explorer.
    padding = ('='*67 + '\n') * 4
  return HttpTextResponse(padding + request.patchset.data)


@patch_required
def patch(request):
  """/<issue>/patch/<patchset>/<patch> - View a raw patch."""
  return patch_helper(request)


def patch_helper(request, nav_type='patch'):
  """Returns a unified diff.

  Args:
    request: Django Request object.
    nav_type: the navigation used in the url (i.e. patch/diff/diff2).  Normally
      the user looks at either unified or side-by-side diffs at one time, going
      through all the files in the same mode.  However, if side-by-side is not
      available for some files, we temporarly switch them to unified view, then
      switch them back when we can.  This way they don't miss any files.

  Returns:
    Whatever respond() returns.
  """
  _add_next_prev(request.patchset, request.patch)
  request.patch.nav_type = nav_type
  parsed_lines = patching.ParsePatchToLines(request.patch.lines)
  if parsed_lines is None:
    return HttpTextResponse('Can\'t parse the patch to lines', status=404)
  rows = engine.RenderUnifiedTableRows(request, parsed_lines)
  return respond(request, 'patch.html',
                 {'patch': request.patch,
                  'patchset': request.patchset,
                  'view_style': 'patch',
                  'rows': rows,
                  'issue': request.issue,
                  'context': _clean_int(request.GET.get('context'), -1),
                  'column_width': _clean_int(request.GET.get('column_width'),
                                             None),
                  })


@image_required
def image(request):
  """/<issue>/content/<patchset>/<patch>/<content> - Return patch's content."""
  response = HttpResponse(request.content.data, content_type=request.mime_type)
  filename = re.sub(
      r'[^\w\.]', '_', request.patch.filename.encode('ascii', 'replace'))
  response['Content-Disposition'] = 'attachment; filename="%s"' % filename
  response['Cache-Control'] = 'no-cache, no-store'
  return response


@patch_required
def download_patch(request):
  """/download/issue<issue>_<patchset>_<patch>.diff - Download patch."""
  return HttpTextResponse(request.patch.text)

def _get_context_for_user(request):
  """Returns the context setting for a user.

  The value is validated against models.CONTEXT_CHOICES.
  If an invalid value is found, the value is overwritten with
  django_settings.DEFAULT_CONTEXT.
  """
  get_param = request.GET.get('context') or None
  if 'context' in request.GET and get_param is None:
    # User wants to see whole file. No further processing is needed.
    return get_param
  if request.user:
    account = models.Account.current_user_account
    default_context = account.default_context
  else:
    default_context = django_settings.DEFAULT_CONTEXT
  context = _clean_int(get_param, default_context)
  if context is not None and context not in models.CONTEXT_CHOICES:
    context = django_settings.DEFAULT_CONTEXT
  return context

def _get_column_width_for_user(request):
  """Returns the column width setting for a user."""
  if request.user:
    account = models.Account.current_user_account
    default_column_width = account.default_column_width
  else:
    default_column_width = django_settings.DEFAULT_COLUMN_WIDTH
  column_width = _clean_int(request.GET.get('column_width'),
                            default_column_width,
                            django_settings.MIN_COLUMN_WIDTH,
                            django_settings.MAX_COLUMN_WIDTH)
  return column_width

def _get_comment_counts(account, patchset):
  """Helper to get comment counts for all patches in a single query.

  The helper returns two dictionaries comments_by_patch and
  drafts_by_patch with patch key as key and comment count as
  value. Patches without comments or drafts are not present in those
  dictionaries.
  """
  # A key-only query won't work because we need to fetch the patch key
  # in the for loop further down.
  comment_query = models.Comment.all()
  comment_query.ancestor(patchset)

  # Get all comment counts with one query rather than one per patch.
  comments_by_patch = {}
  drafts_by_patch = {}
  for c in comment_query:
    pkey = models.Comment.patch.get_value_for_datastore(c)
    if not c.draft:
      comments_by_patch[pkey] = comments_by_patch.setdefault(pkey, 0) + 1
    elif account and c.author == account.user:
      drafts_by_patch[pkey] = drafts_by_patch.setdefault(pkey, 0) + 1

  return comments_by_patch, drafts_by_patch


def _add_next_prev(patchset, patch):
  """Helper to add .next and .prev attributes to a patch object."""
  patch.prev = patch.next = None
  patches = models.Patch.all().filter('patchset =', patchset.key()).order(
      'filename').fetch(1000)
  patchset.patches = patches  # Required to render the jump to select.

  comments_by_patch, drafts_by_patch = _get_comment_counts(
     models.Account.current_user_account, patchset)

  last_patch = None
  next_patch = None
  last_patch_with_comment = None
  next_patch_with_comment = None

  found_patch = False
  for p in patches:
    if p.filename == patch.filename:
      found_patch = True
      continue

    p._num_comments = comments_by_patch.get(p.key(), 0)
    p._num_drafts = drafts_by_patch.get(p.key(), 0)

    if not found_patch:
      last_patch = p
      if p.num_comments > 0 or p.num_drafts > 0:
        last_patch_with_comment = p
    else:
      if next_patch is None:
        next_patch = p
      if p.num_comments > 0 or p.num_drafts > 0:
        next_patch_with_comment = p
        # safe to stop scanning now because the next with out a comment
        # will already have been filled in by some earlier patch
        break

  patch.prev = last_patch
  patch.next = next_patch
  patch.prev_with_comment = last_patch_with_comment
  patch.next_with_comment = next_patch_with_comment


def _add_next_prev2(ps_left, ps_right, patch_right):
  """Helper to add .next and .prev attributes to a patch object."""
  patch_right.prev = patch_right.next = None
  patches = list(models.Patch.gql("WHERE patchset = :1 ORDER BY filename",
                                  ps_right))
  ps_right.patches = patches  # Required to render the jump to select.

  n_comments, n_drafts = _get_comment_counts(
    models.Account.current_user_account, ps_right)

  last_patch = None
  next_patch = None
  last_patch_with_comment = None
  next_patch_with_comment = None

  found_patch = False
  for p in patches:
    if p.filename == patch_right.filename:
      found_patch = True
      continue

    p._num_comments = n_comments.get(p.key(), 0)
    p._num_drafts = n_drafts.get(p.key(), 0)

    if not found_patch:
      last_patch = p
      if ((p.num_comments > 0 or p.num_drafts > 0) and
          ps_left.key().id() in p.delta):
        last_patch_with_comment = p
    else:
      if next_patch is None:
        next_patch = p
      if ((p.num_comments > 0 or p.num_drafts > 0) and
          ps_left.key().id() in p.delta):
        next_patch_with_comment = p
        # safe to stop scanning now because the next with out a comment
        # will already have been filled in by some earlier patch
        break

  patch_right.prev = last_patch
  patch_right.next = next_patch
  patch_right.prev_with_comment = last_patch_with_comment
  patch_right.next_with_comment = next_patch_with_comment

def _get_affected_files(issue, full_diff=False):
  """Helper to return a list of affected files from the latest patchset.

  Args:
    issue: Issue instance.
    full_diff: If true, include the entire diff even if it exceeds 100 lines.

  Returns:
    2-tuple containing a list of affected files, and the diff contents if it
    is less than 100 lines (otherwise the second item is an empty string).
  """
  files = []
  modified_count = 0
  diff = ''
  patchsets = list(issue.patchset_set.order('created'))
  if len(patchsets):
    patchset = patchsets[-1]
    for patch in patchset.patch_set.order('filename'):
      file_str = ''
      if patch.status:
        file_str += patch.status + ' '
      file_str += patch.filename
      files.append(file_str)
      # No point in loading patches if the patchset is too large for email.
      if full_diff or modified_count < 100:
        modified_count += patch.num_added + patch.num_removed

    if full_diff or modified_count < 100:
      diff = patchset.data

  return files, diff


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

PUBLISH_STAFF_FIELDS = ['comp_score', 'send_mail', 'reviewers', 'owners', 'bug_submit']

def _encode_safely(s):
  """Helper to turn a unicode string into 8-bit bytes."""
  if isinstance(s, unicode):
    s = s.encode('utf-8')
  return s


def _patchlines2cache(patchlines, left):
  """Helper that converts return value of ParsePatchToLines for caching.

  Each line in patchlines is (old_line_no, new_line_no, line).  When
  comment is on the left we store the old_line_no, otherwise
  new_line_no.
  """
  if left:
    it = ((old, line) for old, _, line in patchlines)
  else:
    it = ((new, line) for _, new, line in patchlines)
  return dict(it)


def _get_draft_details(request, comments):
  """Helper to display comments with context in the email message."""
  last_key = None
  output = []
  linecache = {}  # Maps (c.patch.key(), c.left) to mapping (lineno, line)
  modified_patches = []

  for c in comments:
    if (c.patch.key(), c.left) != last_key:
      url = request.build_absolute_uri(
        reverse(request, diff, args=[request.issue.key().id(),
                            c.patch.patchset.key().id(),
                            c.patch.filename]))
      output.append('\n%s\nFile %s (%s):' % (url, c.patch.filename,
                                             c.left and "left" or "right"))
      last_key = (c.patch.key(), c.left)
      patch = c.patch
      if patch.no_base_file:
        linecache[last_key] = _patchlines2cache(
          patching.ParsePatchToLines(patch.lines), c.left)
      else:
        try:
          if c.left:
            old_lines = patch.get_content().text.splitlines(True)
            linecache[last_key] = dict(enumerate(old_lines, 1))
          else:
            new_lines = patch.get_patched_content().text.splitlines(True)
            linecache[last_key] = dict(enumerate(new_lines, 1))
        except FetchError:
          linecache[last_key] = _patchlines2cache(
            patching.ParsePatchToLines(patch.lines), c.left)
    context = linecache[last_key].get(c.lineno, '').strip()
    url = request.build_absolute_uri(
      '%s#%scode%d' % (reverse(request, diff, args=[request.issue.key().id(),
                                           c.patch.patchset.key().id(),
                                           c.patch.filename]),
                       c.left and "old" or "new",
                       c.lineno))
    output.append('\n%s\n%s:%d: %s\n%s' % (url, c.patch.filename, c.lineno,
                                           context, c.text.rstrip()))
  if modified_patches:
    db.put(modified_patches)
  return '\n'.join(output)


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


