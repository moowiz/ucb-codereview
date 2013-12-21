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
from view_utils import *
from view_snippets import *
from view_api import *
from view_upload import *
from view_issue_draft import *
from view_diff import *

from view_decorators import *


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






PUBLISH_STAFF_FIELDS = ['comp_score', 'send_mail', 'reviewers', 'owners', 'bug_submit']





