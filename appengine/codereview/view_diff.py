import re

from view_decorators import login_required, patch_filename_required, json_response, patch_required, issue_required
from view_snippets import _get_snippets
from view_users import _get_context_for_user, _get_column_width_for_user
from view_utils import respond

from google.appengine.api import users

import patching
import models
import engine
from exceptions import FetchError

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
