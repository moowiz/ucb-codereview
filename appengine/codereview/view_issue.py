from view_decorators import issue_editor_required, xsrf_required, issue_required, post_required, upload_required, json_response, login_required
from view_utils import _can_view_issue, _clean_int, respond, reverse
from view_issue_draft import _get_draft_comments, _get_draft_details
from view_taskQ import _calculate_delta

import models
import forms

import logging

from django.http import HttpResponseRedirect

from google.appengine.ext import db
from google.appengine.runtime import DeadlineExceededError

@issue_editor_required
@xsrf_required
def edit(request):
  """/<issue>/edit - Edit an issue."""
  issue = request.issue

  form_cls = forms.IssueBaseForm

  if request.method != 'POST':
    reviewers = [reviewer for reviewer in issue.reviewers]
    owners = [owner for owner in issue.owners]
    form = form_cls(initial={'subject': issue.subject,
                             'reviewers': ', '.join(reviewers),
                             'owners': ', '.join(owners),
                             'bug_submit': issue.bug,
                             })
    return respond(request, 'edit.html', {'issue': issue, 'form': form})

  form = form_cls(request.POST)

  if not form.is_valid():
    return respond(request, 'edit.html', {'issue': issue, 'form': form})
  else:
    reviewers = _get_emails(form, 'reviewers')
    owners = _get_emails(form, 'owners')

  cleaned_data = form.cleaned_data

  issue.subject = cleaned_data['subject']
  issue.reviewers = reviewers
  issue.owners = owners
  issue.bug = cleaned_data.get('bug_submit', False)
  issue.put()
  return HttpResponseRedirect(reverse(request, show, args=[issue.key().id()]))

@post_required
@issue_required
@xsrf_required
def delete(request):
  """/<issue>/delete - Delete an issue.  There is no way back."""
  issue = request.issue
  tbd = [issue]
  for cls in [models.PatchSet, models.Patch, models.Comment,
              models.Message, models.Content]:
    tbd += cls.gql('WHERE ANCESTOR IS :1', issue)
  db.delete(tbd)
  return HttpResponseRedirect(reverse(request, mine))

@post_required
@issue_editor_required
@xsrf_required
def close(request):
  """/<issue>/close - Close an issue."""
  issue = request.issue
  issue.closed = True
  if request.method == 'POST':
    new_description = request.POST.get('description')
    if new_description:
      issue.description = new_description
  issue.put()
  return HttpTextResponse('Closed')

@issue_required
@upload_required
def description(request):
  """/<issue>/description - Gets/Sets an issue's description.

  Used by upload.py or similar scripts.
  """
  if request.method != 'POST':
    description = request.issue.description or ""
    return HttpTextResponse(description)
  if not request.issue.user_can_edit(request.user):
    if not IS_DEV:
      return HttpTextResponse('Login required', status=401)
  issue = request.issue
  issue.description = request.POST.get('description')
  issue.put()
  return HttpTextResponse('')


@issue_required
@upload_required
@json_response
def fields(request):
  """/<issue>/fields - Gets/Sets fields on the issue.

  Used by upload.py or similar scripts for partial updates of the issue
  without a patchset..
  """
  # Only recognizes a few fields for now.
  if request.method != 'POST':
    fields = request.GET.getlist('field')
    response = {}
    if 'reviewers' in fields:
      response['reviewers'] = request.issue.reviewers or []
    if 'description' in fields:
      response['description'] = request.issue.description
    if 'subject' in fields:
      response['subject'] = request.issue.subject
    return response

  if not request.issue.user_can_edit(request.user):
    if not IS_DEV:
      return HttpTextResponse('Login required', status=401)
  fields = json.loads(request.POST.get('fields'))
  issue = request.issue
  if 'description' in fields:
    issue.description = fields['description']
  if 'reviewers' in fields:
    issue.reviewers = _get_emails_from_raw(fields['reviewers'])
  if 'subject' in fields:
    issue.subject = fields['subject']
  issue.put()
  return HttpTextResponse('')

@login_required
@issue_required
@xsrf_required
def publish(request):
  """ /<issue>/publish - Publish draft comments and send mail."""
  issue = request.issue
  form_class = forms.PublishForm
  draft_message = None
  if not request.POST.get('message_only', None):
    query = models.Message.gql(('WHERE issue = :1 AND sender = :2 '
                                'AND draft = TRUE'), issue,
                               request.user.email())
    draft_message = query.get()
  if request.method != 'POST':
    owners = issue.owners[:]
    reviewers = issue.reviewers[:]
    tbd, comments = _get_draft_comments(request, issue, True)
    preview = _get_draft_details(request, comments)
    if draft_message is None:
      msg = ''
    else:
      msg = draft_message.text
    form = form_class(initial={'subject': issue.subject,
                               'owners': ', '.join(owners),
                               'send_mail': request.is_staff,
                               'message': msg,
                               'comp_score': issue.comp_score,
                               'reviewers': ', '.join(reviewers),
                               })
    if not request.is_staff:
        for it in PUBLISH_STAFF_FIELDS:
          del form.fields[it]
    return respond(request, 'publish.html', {'form': form,
                                             'issue': issue,
                                             'preview': preview,
                                             'draft_message': draft_message,
                                             })

  form = form_class(request.POST)
  if not form.is_valid():
    return respond(request, 'publish.html', {'form': form, 'issue': issue})
  if form.is_valid() and not form.cleaned_data.get('message_only', False):
    owners = _get_emails(form, 'owners')
  else:
    owners = issue.owners
  if not form.is_valid():
    return respond(request, 'publish.html', {'form': form, 'issue': issue})
  if not form.cleaned_data.get('message_only', False):
    tbd, comments = _get_draft_comments(request, issue)
  else:
    tbd = []
    comments = []
  issue.update_comment_count(len(comments))
  issue.set_comp_score(form.cleaned_data.get('comp_score', -1))
  issue.bug = form.cleaned_data.get('bug_submit', False)
  tbd.append(issue)

  if comments:
    logging.warn('Publishing %d comments', len(comments))
  msg = _make_message(request, issue,
                      form.cleaned_data['message'],
                      comments,
                      form.cleaned_data['send_mail'],
                      draft=draft_message,
                      in_reply_to=form.cleaned_data.get('in_reply_to'))
  tbd.append(msg)

  for obj in tbd:

    db.put(obj)


  # There are now no comments here (modulo race conditions)
  models.Account.current_user_account.update_drafts(issue, 0)
  if form.cleaned_data.get('no_redirect', False):
    return HttpTextResponse('OK')
  return HttpResponseRedirect(reverse(request, show, args=[issue.key().id()]))

@post_required
@login_required
@xsrf_required
@issue_required
def star(request):
  """Add a star to an Issue."""
  account = models.Account.current_user_account
  if account.stars is None:
    account.stars = []
  id = request.issue.key().id()
  if id not in account.stars:
    account.stars.append(id)
    account.put()
  return respond(request, 'issue_star.html', {'issue': request.issue})


@post_required
@login_required
@issue_required
@xsrf_required
def unstar(request):
  """Remove the star from an Issue."""
  account = models.Account.current_user_account
  if account.stars is None:
    account.stars = []
  id = request.issue.key().id()
  if id in account.stars:
    account.stars[:] = [i for i in account.stars if i != id]
    account.put()
  return respond(request, 'issue_star.html', {'issue': request.issue})

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

#put at the end to avoid a circular dependency
from view_forms import _get_emails
from view_mail import _make_message
