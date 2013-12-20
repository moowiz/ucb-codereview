
@login_required
@patch_filename_required
def diff(request):
  """/<issue>/diff/<patchset>/<patch> - View a patch as a side-by-side diff"""
  if request.patch.no_base_file:
    # Can't show side-by-side diff since we don't have the base file.  Show the
    # unified diff instead.
    return patch_helper(request, 'diff')

  patchset = request.patchset
  patch = request.patch

  patchsets = list(request.issue.patchset_set.order('created'))

  snippets, allow_snippets = _get_snippets(request)
  my_email = users.get_current_user().email()
  my_snippets = [s for s in snippets if s.created_by and s.created_by.email() == my_email]

  context = _get_context_for_user(request)
  column_width = _get_column_width_for_user(request)
  if patch.is_binary:
    rows = None
  else:
    try:
      rows = _get_diff_table_rows(request, patch, context, column_width)
    except FetchError, err:
      return HttpTextResponse(str(err), status=404)

  _add_next_prev(patchset, patch)
  return respond(request, 'diff.html',
                 {'issue': request.issue,
                  'patchset': patchset,
                  'patch': patch,
                  'view_style': 'diff',
                  'rows': rows,
                  'context': context,
                  'context_values': models.CONTEXT_CHOICES,
                  'column_width': column_width,
                  'patchsets': patchsets,
                  'snippets': snippets,
                  'allow_snippets': allow_snippets,
                  'my_snippets': my_snippets
                  })


def _get_diff_table_rows(request, patch, context, column_width):
  """Helper function that returns rendered rows for a patch.

  Raises:
    FetchError if patch parsing or download of base files fails.
  """
  chunks = patching.ParsePatchToChunks(patch.lines, patch.filename)
  if chunks is None:
    raise FetchError('Can\'t parse the patch to chunks')

  # Possible FetchErrors are handled in diff() and diff_skipped_lines().
  content = request.patch.get_content()

  rows = list(engine.RenderDiffTableRows(request, content.lines,
                                         chunks, patch,
                                         context=context,
                                         colwidth=column_width))
  if rows and rows[-1] is None:
    del rows[-1]
    # Get rid of content, which may be bad
    if content.is_uploaded and content.text != None:
      # Don't delete uploaded content, otherwise get_content()
      # will fetch it.
      content.is_bad = True
      content.text = None
      content.put()
    else:
      content.delete()
      request.patch.content = None
      request.patch.put()

  return rows


@patch_required
@json_response
def diff_skipped_lines(request, id_before, id_after, where, column_width):
  """/<issue>/diff/<patchset>/<patch> - Returns a fragment of skipped lines.

  *where* indicates which lines should be expanded:
    'b' - move marker line to bottom and expand above
    't' - move marker line to top and expand below
    'a' - expand all skipped lines
  """
  patch = request.patch
  if where == 'a':
    context = None
  else:
    context = _get_context_for_user(request) or 100

  column_width = _clean_int(column_width, django_settings.DEFAULT_COLUMN_WIDTH,
                            django_settings.MIN_COLUMN_WIDTH,
                            django_settings.MAX_COLUMN_WIDTH)

  try:
    rows = _get_diff_table_rows(request, patch, None, column_width)
  except FetchError, err:
    return HttpTextResponse('Error: %s; please report!' % err, status=500)
  return _get_skipped_lines_response(rows, id_before, id_after, where, context)


# there's no easy way to put a control character into a regex, so brute-force it
# this is all control characters except \r, \n, and \t
_badchars_re = re.compile(
    r'[\000\001\002\003\004\005\006\007\010\013\014\016\017'
    r'\020\021\022\023\024\025\026\027\030\031\032\033\034\035\036\037]')


def _strip_invalid_xml(s):
  """Remove control chars other than \r\n\t from a string to be put in XML."""
  if _badchars_re.search(s):
    return ''.join(c for c in s if c >= ' ' or c in '\r\n\t')
  else:
    return s


def _get_skipped_lines_response(rows, id_before, id_after, where, context):
  """Helper function that returns response data for skipped lines"""
  response_rows = []
  id_before_start = int(id_before)
  id_after_end = int(id_after)
  if context is not None:
    id_before_end = id_before_start+context
    id_after_start = id_after_end-context
  else:
    id_before_end = id_after_start = None

  for row in rows:
    m = re.match('^<tr( name="hook")? id="pair-(?P<rowcount>\d+)">', row)
    if m:
      curr_id = int(m.groupdict().get("rowcount"))
      # expand below marker line
      if (where == 'b'
          and curr_id > id_after_start and curr_id <= id_after_end):
        response_rows.append(row)
      # expand above marker line
      elif (where == 't'
            and curr_id >= id_before_start and curr_id < id_before_end):
        response_rows.append(row)
      # expand all skipped lines
      elif (where == 'a'
            and curr_id >= id_before_start and curr_id <= id_after_end):
        response_rows.append(row)
      if context is not None and len(response_rows) >= 2*context:
        break

  # Create a usable structure for the JS part
  response = []
  response_rows =  [_strip_invalid_xml(r) for r in response_rows]
  dom = ElementTree.parse(StringIO('<div>%s</div>' % "".join(response_rows)))
  for node in dom.getroot().getchildren():
    content = [[x.items(), x.text] for x in node.getchildren()]
    response.append([node.items(), content])
  return response


def _get_diff2_data(request, ps_left_id, ps_right_id, patch_id, context,
                    column_width, patch_filename=None):
  """Helper function that returns objects for diff2 views"""
  ps_left = models.PatchSet.get_by_id(int(ps_left_id), parent=request.issue)
  if ps_left is None:
    return HttpTextResponse(
        'No patch set exists with that id (%s)' % ps_left_id, status=404)
  ps_left.issue = request.issue
  ps_right = models.PatchSet.get_by_id(int(ps_right_id), parent=request.issue)
  if ps_right is None:
    return HttpTextResponse(
        'No patch set exists with that id (%s)' % ps_right_id, status=404)
  ps_right.issue = request.issue
  if patch_id is not None:
    patch_right = models.Patch.get_by_id(int(patch_id), parent=ps_right)
  else:
    patch_right = None
  if patch_right is not None:
    patch_right.patchset = ps_right
    if patch_filename is None:
      patch_filename = patch_right.filename
  # Now find the corresponding patch in ps_left
  patch_left = models.Patch.gql('WHERE patchset = :1 AND filename = :2',
                                ps_left, patch_filename).get()

  if patch_left:
    try:
      new_content_left = patch_left.get_patched_content()
    except FetchError, err:
      return HttpTextResponse(str(err), status=404)
    lines_left = new_content_left.lines
  elif patch_right:
    lines_left = patch_right.get_content().lines
  else:
    lines_left = []

  if patch_right:
    try:
      new_content_right = patch_right.get_patched_content()
    except FetchError, err:
      return HttpTextResponse(str(err), status=404)
    lines_right = new_content_right.lines
  elif patch_left:
    lines_right = patch_left.get_content().lines
  else:
    lines_right = []

  rows = engine.RenderDiff2TableRows(request,
                                     lines_left, patch_left,
                                     lines_right, patch_right,
                                     context=context,
                                     colwidth=column_width)
  rows = list(rows)
  if rows and rows[-1] is None:
    del rows[-1]

  return dict(patch_left=patch_left, patch_right=patch_right,
              ps_left=ps_left, ps_right=ps_right, rows=rows)


@login_required
@issue_required
def diff2(request, ps_left_id, ps_right_id, patch_filename):
  """/<issue>/diff2/... - View the delta between two different patch sets."""
  context = _get_context_for_user(request)
  column_width = _get_column_width_for_user(request)

  ps_right = models.PatchSet.get_by_id(int(ps_right_id), parent=request.issue)
  patch_right = None

  if ps_right:
    patch_right = models.Patch.gql('WHERE patchset = :1 AND filename = :2',
                                   ps_right, patch_filename).get()

  if patch_right:
    patch_id = patch_right.key().id()
  elif patch_filename.isdigit():
    # Perhaps it's an ID that's passed in, based on the old URL scheme.
    patch_id = int(patch_filename)
  else:  # patch doesn't exist in this patchset
    patch_id = None

  data = _get_diff2_data(request, ps_left_id, ps_right_id, patch_id, context,
                         column_width, patch_filename)
  if isinstance(data, HttpResponse) and data.status_code != 302:
    return data

  patchsets = list(request.issue.patchset_set.order('created'))

  if data["patch_right"]:
    _add_next_prev2(data["ps_left"], data["ps_right"], data["patch_right"])
  return respond(request, 'diff2.html',
                 {'issue': request.issue,
                  'ps_left': data["ps_left"],
                  'patch_left': data["patch_left"],
                  'ps_right': data["ps_right"],
                  'patch_right': data["patch_right"],
                  'rows': data["rows"],
                  'patch_id': patch_id,
                  'context': context,
                  'context_values': models.CONTEXT_CHOICES,
                  'column_width': column_width,
                  'patchsets': patchsets,
                  'filename': patch_filename,
                  })


@issue_required
@json_response
def diff2_skipped_lines(request, ps_left_id, ps_right_id, patch_id,
                        id_before, id_after, where, column_width):
  """/<issue>/diff2/... - Returns a fragment of skipped lines"""
  column_width = _clean_int(column_width, django_settings.DEFAULT_COLUMN_WIDTH,
                            django_settings.MIN_COLUMN_WIDTH,
                            django_settings.MAX_COLUMN_WIDTH)

  if where == 'a':
    context = None
  else:
    context = _get_context_for_user(request) or 100

  data = _get_diff2_data(request, ps_left_id, ps_right_id, patch_id, 10000,
                         column_width)
  if isinstance(data, HttpResponse) and data.status_code != 302:
    return data
  return _get_skipped_lines_response(data["rows"], id_before, id_after,
                                     where, context)
