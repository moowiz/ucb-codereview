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
