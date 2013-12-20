@login_required
@xsrf_required
def use_uploadpy(request):
  """Show an intermediate page about upload.py."""
  if request.method == 'POST':
    if 'disable_msg' in request.POST:
      models.Account.current_user_account.put()
    if 'download' in request.POST:
      url = reverse(request, customized_upload_py)
    else:
      url = reverse(request, new)
    return HttpResponseRedirect(url)
  return respond(request, 'use_uploadpy.html')


@post_required
@upload_required
def upload(request):
  """/upload - Like new() or add(), but from the upload.py script.

  This generates a text/plain response.
  """
  if request.user is None:
    if IS_DEV:
      request.user = users.User(request.POST.get('user', 'test@example.com'))
    else:
      return HttpTextResponse('Login required', status=401)
  # Check against old upload.py usage.
  if request.POST.get('num_parts') > 1:
    return HttpTextResponse('Upload.py is too old, get the latest version.')
  form = forms.UploadForm(request.POST, request.FILES)
  issue = None
  patchset = None
  if form.is_valid():
    issue_id = form.cleaned_data['issue']
    if issue_id:
      action = 'updated'
      issue = models.Issue.get_by_id(issue_id, form.semester)
      if issue is None:
        form.errors['issue'] = ['No issue exists with that id (%s)' %
                                issue_id]
      elif not form.cleaned_data.get('content_upload'):
        form.errors['issue'] = ['Base files upload required for that issue.']
        issue = None
      else:
        patchset = _add_patchset_from_form(request, issue, form, 'subject')
        if not patchset:
            issue = None
    else:
      action = 'created'
      issue, patchset = _make_new(request, form)
  if issue is None:
    msg = 'Issue creation errors: %s' % repr(form.errors)
  else:
    msg = ('Issue %s. URL: %s' %
           (action,
            request.build_absolute_uri(
              _reverse(show, args=[django_settings.CURRENT_SEMESTER, issue.key().id()]))))
    if (form.cleaned_data.get('content_upload') or
        form.cleaned_data.get('separate_patches')):
      # Extend the response message: 2nd line is patchset id.
      msg +="\n%d" % patchset.key().id()
      if form.cleaned_data.get('content_upload'):
        # Extend the response: additional lines are the expected filenames.
        issue.put()

        base_hashes = {}
        for file_info in form.cleaned_data.get('base_hashes').split("|"):
          if not file_info:
            break
          checksum, filename = file_info.split(":", 1)
          base_hashes[filename] = checksum

        content_entities = []
        new_content_entities = []
        patches = list(patchset.patch_set)
        existing_patches = {}
        patchsets = list(issue.patchset_set)
        if len(patchsets) > 1:
          # Only check the last uploaded patchset for speed.
          last_patch_set = patchsets[-2].patch_set
          patchsets = None  # Reduce memory usage.
          for opatch in last_patch_set:
            if opatch.content:
              existing_patches[opatch.filename] = opatch
        for patch in patches:
          content = None
          # Check if the base file is already uploaded in another patchset.
          if (patch.filename in base_hashes and
              patch.filename in existing_patches and
              (base_hashes[patch.filename] ==
               existing_patches[patch.filename].content.checksum)):
            content = existing_patches[patch.filename].content
            patch.status = existing_patches[patch.filename].status
            patch.is_binary = existing_patches[patch.filename].is_binary
          if not content:
            content = models.Content(is_uploaded=True, parent=patch)
            new_content_entities.append(content)
          content_entities.append(content)
        existing_patches = None  # Reduce memory usage.
        if new_content_entities:
          db.put(new_content_entities)

        for patch, content_entity in zip(patches, content_entities):
          patch.content = content_entity
          id_string = patch.key().id()
          if content_entity not in new_content_entities:
            # Base file not needed since we reused a previous upload.  Send its
            # patch id in case it's a binary file and the new content needs to
            # be uploaded.  We mark this by prepending 'nobase' to the id.
            id_string = "nobase_" + str(id_string)
          msg += "\n%s %s" % (id_string, patch.filename)
        db.put(patches)
  return HttpTextResponse(msg)


@handle_year
@post_required
@patch_required
@upload_required
def upload_content(request):
  """/<issue>/upload_content/<patchset>/<patch> - Upload base file contents.

  Used by upload.py to upload base files.
  """
  form = forms.UploadContentForm(request.POST, request.FILES)
  if not form.is_valid():
    return HttpTextResponse(
        'ERROR: Upload content errors:\n%s' % repr(form.errors))
  if request.user is None:
    if IS_DEV:
      request.user = users.User(request.POST.get('user', 'test@example.com'))
    else:
      return HttpTextResponse('Error: Login required', status=401)
  patch = request.patch
  patch.status = form.cleaned_data['status']
  patch.is_binary = form.cleaned_data['is_binary']
  patch.put()

  if form.cleaned_data['is_current']:
    if patch.patched_content:
      return HttpTextResponse('ERROR: Already have current content.')
    content = models.Content(is_uploaded=True, parent=patch)
    content.put()
    patch.patched_content = content
    patch.put()
  else:
    content = patch.content

  if form.cleaned_data['file_too_large']:
    content.file_too_large = True
  else:
    data = form.get_uploaded_content()
    h = hashlib.md5()
    h.update(data)
    checksum = h.hexdigest()
    if checksum != request.POST.get('checksum'):
      content.is_bad = True
      content.put()
      return HttpTextResponse('ERROR: Checksum mismatch.')
    if patch.is_binary:
      content.data = data
    else:
      content.text = utils.to_dbtext(utils.unify_linebreaks(data))
    content.checksum = checksum
  content.put()
  return HttpTextResponse('OK')


@handle_year
@post_required
@patchset_required
@upload_required
def upload_patch(request):
  """/<issue>/upload_patch/<patchset> - Upload patch to patchset.

  Used by upload.py to upload a patch when the diff is too large to upload all
  together.
  """
  if request.user is None:
    if IS_DEV:
      request.user = users.User(request.POST.get('user', 'test@example.com'))
    else:
      return HttpTextResponse('Error: Login required', status=401)
  form = forms.UploadPatchForm(request.POST, request.FILES)
  if not form.is_valid():
    return HttpTextResponse(
        'ERROR: Upload patch errors:\n%s' % repr(form.errors))
  patchset = request.patchset
  if patchset.data:
    return HttpTextResponse(
        'ERROR: Can\'t upload patches to patchset with data.')
  text = utils.to_dbtext(utils.unify_linebreaks(form.get_uploaded_patch()))
  patch = models.Patch(patchset=patchset,
                       text=text,
                       filename=form.cleaned_data['filename'], parent=patchset)
  patch.put()
  if form.cleaned_data.get('content_upload'):
    content = models.Content(is_uploaded=True, parent=patch)
    content.put()
    patch.content = content
    patch.put()

  msg = 'OK\n' + str(patch.key().id())
  return HttpTextResponse(msg)


@handle_year
@post_required
@issue_required
@upload_required
def upload_complete(request, patchset_id=None):
  """/<issue>/upload_complete/<patchset> - Patchset upload is complete.
     /<issue>/upload_complete/ - used when no base files are uploaded.

  The following POST parameters are handled:

   - send_mail: If 'yes', a notification mail will be send.
   - attach_patch: If 'yes', the patches will be attached to the mail.
  """
  if patchset_id is not None:
    patchset = models.PatchSet.get_by_id(int(patchset_id),
                                         parent=request.issue)
    if patchset is None:
      return HttpTextResponse(
          'No patch set exists with that id (%s)' % patchset_id, status=403)
    # Add delta calculation task.
    taskqueue.add(url=reverse(request, calculate_delta),
                  params={'key': str(patchset.key())},
                  queue_name='deltacalculation')
  else:
    patchset = None
  # Check for completeness
  errors = []
  # Create (and send) a message if needed.
  if request.POST.get('send_mail') == 'yes' or request.POST.get('message'):
    msg = _make_message(request, request.issue, request.POST.get('message', ''),
                        send_mail=(request.POST.get('send_mail', '') == 'yes'))
    msg.put()
  if errors:
    msg = ('The following errors occured:\n%s\n'
           'Try to upload the changeset again.'
           % '\n'.join(errors))
    status = 500
  else:
    msg = 'OK'
    status = 200
  return HttpTextResponse(msg, status=status)


def customized_upload_py(request):
  """/static/upload.py - Return patched upload.py with appropiate auth type and
  default review server setting.

  This is used to let the user download a customized upload.py script
  for hosted Rietveld instances.
  """
  f = open(django_settings.UPLOAD_PY_SOURCE)
  source = f.read()
  f.close()

  # When served from a Google Apps instance, the account namespace needs to be
  # switched to "Google Apps only".
  if ('AUTH_DOMAIN' in request.META
      and request.META['AUTH_DOMAIN'] != 'gmail.com'):
    source = source.replace('AUTH_ACCOUNT_TYPE = "GOOGLE"',
                            'AUTH_ACCOUNT_TYPE = "HOSTED"')

  # On a non-standard instance, the default review server is changed to the
  # current hostname. This might give weird results when using versioned appspot
  # URLs (eg. 1.latest.codereview.appspot.com), but this should only affect
  # testing.
  if request.META['HTTP_HOST'] != 'codereview.appspot.com':
    review_server = request.META['HTTP_HOST']
    if request.is_secure():
      review_server = 'https://' + review_server
    source = source.replace('DEFAULT_REVIEW_SERVER = "codereview.appspot.com"',
                            'DEFAULT_REVIEW_SERVER = "%s"' % review_server)

  return HttpResponse(source, content_type='text/x-python; charset=utf-8')