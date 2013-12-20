@login_required
@issue_required
def draft_message(request):
  """/<issue>/draft_message - Retrieve, modify and delete draft messages.

  Note: creating or editing draft messages is *not* XSRF-protected,
  because it is not unusual to come back after hours; the XSRF tokens
  time out after 1 or 2 hours.  The final submit of the drafts for
  others to view *is* XSRF-protected.
  """
  query = models.Message.gql(('WHERE issue = :1 AND sender = :2 '
                              'AND draft = TRUE'),
                             request.issue, request.user.email())
  if query.count() == 0:
    draft_message = None
  else:
    draft_message = query.get()
  if request.method == 'GET':
    return _get_draft_message(draft_message)
  elif request.method == 'POST':
    return _post_draft_message(request, draft_message)
  elif request.method == 'DELETE':
    return _delete_draft_message(draft_message)
  return HttpTextResponse('An error occurred.', status=500)


def _get_draft_message(draft):
  """Handles GET requests to /<issue>/draft_message.

  Arguments:
    draft: A Message instance or None.

  Returns the content of a draft message or an empty string if draft is None.
  """
  return HttpTextResponse(draft.text if draft else '')


def _post_draft_message(request, draft):
  """Handles POST requests to /<issue>/draft_message.

  If draft is None a new message is created.

  Arguments:
    request: The current request.
    draft: A Message instance or None.
  """
  if draft is None:
    draft = models.Message(issue=request.issue, parent=request.issue,
                           sender=request.user.email(), draft=True)
  draft.text = request.POST.get('reviewmsg')
  draft.put()
  return HttpTextResponse(draft.text)


def _delete_draft_message(draft):
  """Handles DELETE requests to /<issue>/draft_message.

  Deletes a draft message.

  Arguments:
    draft: A Message instance or None.
  """
  if draft is not None:
    draft.delete()
  return HttpTextResponse('OK')

@post_required
def inline_draft(request):
  """/inline_draft - Ajax handler to submit an in-line draft comment.

  This wraps _inline_draft(); all exceptions are logged and cause an
  abbreviated response indicating something went wrong.

  Note: creating or editing draft comments is *not* XSRF-protected,
  because it is not unusual to come back after hours; the XSRF tokens
  time out after 1 or 2 hours.  The final submit of the drafts for
  others to view *is* XSRF-protected.
  """
  try:
    return _inline_draft(request)
  except Exception, err:
    logging.exception('Exception in inline_draft processing:')
    # TODO(guido): return some kind of error instead?
    # Return HttpResponse for now because the JS part expects
    # a 200 status code.
    return HttpHtmlResponse(
        '<font color="red">Error: %s; please report!</font>' %
        err.__class__.__name__)


def _inline_draft(request):
  """Helper to submit an in-line draft comment."""
  # TODO(guido): turn asserts marked with XXX into errors
  # Don't use @login_required, since the JS doesn't understand redirects.
  if not request.user:
    # Don't log this, spammers have started abusing this.
    return HttpTextResponse('Not logged in')
  snapshot = request.POST.get('snapshot')
  assert snapshot in ('old', 'new'), repr(snapshot)
  left = (snapshot == 'old')
  side = request.POST.get('side')
  assert side in ('a', 'b'), repr(side)  # Display left (a) or right (b)
  issue_id = int(request.POST['issue'])
  issue = models.Issue.get_by_id(issue_id, request.semester)
  assert issue  # XXX
  patchset_id = int(request.POST.get('patchset') or
                    request.POST[side == 'a' and 'ps_left' or 'ps_right'])
  patchset = models.PatchSet.get_by_id(int(patchset_id), parent=issue)
  assert patchset  # XXX
  patch_id = int(request.POST.get('patch') or
                 request.POST[side == 'a' and 'patch_left' or 'patch_right'])
  patch = models.Patch.get_by_id(int(patch_id), parent=patchset)
  assert patch  # XXX
  text = request.POST.get('text')
  lineno = int(request.POST['lineno'])
  message_id = request.POST.get('message_id')
  comment = None
  if message_id:
    comment = models.Comment.get_by_key_name(message_id, parent=patch)
    if comment is None or not comment.draft or comment.author != request.user:
      comment = None
      message_id = None
  if not message_id:
    # Prefix with 'z' to avoid key names starting with digits.
    message_id = 'z' + binascii.hexlify(_random_bytes(16))

  if not text.rstrip():
    if comment is not None:
      assert comment.draft and comment.author == request.user
      comment.delete()  # Deletion
      comment = None
      # Re-query the comment count.
      models.Account.current_user_account.update_drafts(issue)
  else:
    if comment is None:
      comment = models.Comment(key_name=message_id, parent=patch)
    comment.patch = patch
    comment.lineno = lineno
    comment.left = left
    comment.text = db.Text(text)
    comment.message_id = message_id
    comment.put()
    # The actual count doesn't matter, just that there's at least one.
    models.Account.current_user_account.update_drafts(issue, 1)

  query = models.Comment.gql(
      'WHERE patch = :patch AND lineno = :lineno AND left = :left '
      'ORDER BY date',
      patch=patch, lineno=lineno, left=left)
  comments = list(c for c in query if not c.draft or c.author == request.user)
  comments.append(comment)
  if not comments:
    return HttpTextResponse(' ')
  for c in comments:
    if c:
      c.complete()
  return render_to_response('inline_comment.html',
                            {'user': request.user,
                             'patch': patch,
                             'patchset': patchset,
                             'issue': issue,
                             'comments': comments,
                             'lineno': lineno,
                             'snapshot': snapshot,
                             'side': side,
                             'semester': request.semester,
                             },
                            context_instance=RequestContext(request))

def _get_draft_comments(request, issue, preview=False):
  """Helper to return objects to put() and a list of draft comments.

  If preview is True, the list of objects to put() is empty to avoid changes
  to the datastore.

  Args:
    request: Django Request object.
    issue: Issue instance.
    preview: Preview flag (default: False).

  Returns:
    2-tuple (put_objects, comments).
  """
  comments = []
  tbd = []
  # XXX Should request all drafts for this issue once, now we can.
  for patchset in issue.patchset_set.order('created'):
    ps_comments = list(models.Comment.gql(
        'WHERE ANCESTOR IS :1 AND author = :2 AND draft = TRUE',
        patchset, request.user))
    if ps_comments:
      patches = dict((p.key(), p) for p in patchset.patch_set)
      for p in patches.itervalues():
        p.patchset = patchset
      for c in ps_comments:
        c.draft = False
        # Get the patch key value without loading the patch entity.
        # NOTE: Unlike the old version of this code, this is the
        # recommended and documented way to do this!
        pkey = models.Comment.patch.get_value_for_datastore(c)
        if pkey in patches:
          patch = patches[pkey]
          c.patch = patch
      if not preview:
        tbd.append(ps_comments)
        patchset.update_comment_count(len(ps_comments))
        tbd.append(patchset)
      ps_comments.sort(key=lambda c: (c.patch.filename, not c.left,
                                      c.lineno, c.date))
      comments += ps_comments
  return tbd, comments