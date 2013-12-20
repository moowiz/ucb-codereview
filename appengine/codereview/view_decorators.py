import urllib

from views_util import HttpTextResponse
import models

from google.appengine.api import users

from django.http import HttpRedirectResponse

def post_required(func):
  """Decorator that returns an error unless request.method == 'POST'."""

  @handle_year
  def post_wrapper(request, *args, **kwds):
    if request.method != 'POST':
      return HttpTextResponse('This requires a POST request.', status=405)
    return func(request, *args, **kwds)

  return post_wrapper


def login_required(func):
  """Decorator that redirects to the login page if you're not logged in."""

  @handle_year
  def login_wrapper(request, *args, **kwds):
    if request.user is None:
      return HttpResponseRedirect(
          users.create_login_url(request.get_full_path().encode('utf-8')))
    return func(request, *args, **kwds)

  return login_wrapper


def xsrf_required(func):
  """Decorator to check XSRF token.

  This only checks if the method is POST; it lets other method go
  through unchallenged.  Apply after @login_required and (if
  applicable) @post_required.  This decorator is mutually exclusive
  with @upload_required.
  """

  def xsrf_wrapper(request, *args, **kwds):
    if request.method == 'POST':
      post_token = request.POST.get('xsrf_token')
      if not post_token:
        return HttpTextResponse('Missing XSRF token.', status=403)
      account = models.Account.current_user_account
      if not account:
        return HttpTextResponse('Must be logged in for XSRF check.', status=403)
      xsrf_token = account.get_xsrf_token()
      if post_token != xsrf_token:
        # Try the previous hour's token
        xsrf_token = account.get_xsrf_token(-1)
        if post_token != xsrf_token:
          msg = [u'Invalid XSRF token.']
          if request.POST:
            msg.extend([u'',
                        u'However, this was the data posted to the server:',
                        u''])
            for key in request.POST:
              msg.append(u'%s: %s' % (key, request.POST[key]))
            msg.extend([u'', u'-'*10,
                        u'Please reload the previous page and post again.'])
          return HttpTextResponse(u'\n'.join(msg), status=403)
    return func(request, *args, **kwds)

  return xsrf_wrapper


def upload_required(func):
  """Decorator for POST requests from the upload.py script.

  Right now this is for documentation only, but eventually we should
  change this to insist on a special header that JavaScript cannot
  add, to prevent XSRF attacks on these URLs.  This decorator is
  mutually exclusive with @xsrf_required.
  """
  return func


def admin_required(func):
  """Decorator that insists that you're logged in as administratior."""

  def admin_wrapper(request, *args, **kwds):
    if request.user is None:
      return HttpResponseRedirect(
          users.create_login_url(request.get_full_path().encode('utf-8')))
    if not request.user_is_admin:
      return HttpTextResponse(
          'You must be admin in for this function', status=403)
    return func(request, *args, **kwds)

  return admin_wrapper

def handle_year(func):
  """Decorator that insists that you're logged in as administratior."""

  def year_wrapper(request, *args, **kwds):
    if 'semester' in kwds:
      popped = kwds.pop('semester')
      sem = models.Semester.all().filter('name =', popped).get()
      if not sem:
        sem = models.Semester(key_name='<%s>'%popped, name=popped)
        sem.put()
      request.semester = sem
    return func(request, *args, **kwds)

  return year_wrapper


def issue_required(func):
  """Decorator that processes the issue_id handler argument."""

  @handle_year
  def issue_wrapper(request, issue_id, *args, **kwds):
    issue = models.Issue.get_by_id(int(issue_id), request.semester)
    if issue is None:
      return HttpTextResponse(
          'No issue exists with that id (%s) in this semester (%s)' % (issue_id, request.semester.name), status=404)
    models.Issue.current_issue = request.issue = issue
    return func(request, *args, **kwds)

  return issue_wrapper


def user_key_required(func):
  """Decorator that processes the user handler argument."""

  @handle_year
  def user_key_wrapper(request, user_key, *args, **kwds):
    user_key = urllib.unquote(user_key)
    if '@' in user_key:
      request.user_to_show = users.User(user_key)
    else:
      account = models.Account.get_account_for_nickname(user_key)
      if not account:
        logging.info("account not found for nickname %s" % user_key)
        return HttpTextResponse(
            'No user found with that key (%s)' % urllib.quote(user_key),
            status=404)
      request.user_to_show = account.user
    return func(request, *args, **kwds)

  return user_key_wrapper

def staff_required(func):
    """Decorator that insists the user is staff"""

    @login_required
    def staff_required_wrapper(request, *args, **kwds):
        if not request.is_staff:
            return HttpTextResponse('You do not have permission to view this page', status=403)
        return func(request, *args, **kwds)
    return staff_required_wrapper


def issue_editor_required(func):
  """Decorator that processes the issue_id argument and insists the user has
  permission to edit it."""

  @login_required
  @issue_required
  def issue_editor_wrapper(request, *args, **kwds):
    if not request.issue.user_can_edit(request.user):
      return HttpTextResponse(
          'You do not have permission to edit this issue', status=403)
    return func(request, *args, **kwds)

  return issue_editor_wrapper


def patchset_required(func):
  """Decorator that processes the patchset_id argument."""

  @issue_required
  def patchset_wrapper(request, patchset_id, *args, **kwds):
    patchset = models.PatchSet.get_by_id(int(patchset_id), parent=request.issue)
    if patchset is None:
      return HttpTextResponse(
          'No patch set exists with that id (%s)' % patchset_id, status=404)
    patchset.issue = request.issue
    request.patchset = patchset
    return func(request, *args, **kwds)

  return patchset_wrapper



def patch_required(func):
  """Decorator that processes the patch_id argument."""

  @patchset_required
  def patch_wrapper(request, patch_id, *args, **kwds):
    patch = models.Patch.get_by_id(int(patch_id), parent=request.patchset)
    if patch is None:
      return HttpTextResponse(
          'No patch exists with that id (%s/%s)' %
          (request.patchset.key().id(), patch_id),
          status=404)
    patch.patchset = request.patchset
    request.patch = patch
    return func(request, *args, **kwds)

  return patch_wrapper


def patch_filename_required(func):
  """Decorator that processes the patch_id argument."""

  @patchset_required
  def patch_wrapper(request, patch_filename, *args, **kwds):
    patch = models.Patch.gql('WHERE patchset = :1 AND filename = :2',
                             request.patchset, patch_filename).get()
    if patch is None and patch_filename.isdigit():
      # It could be an old URL which has a patch ID instead of a filename
      patch = models.Patch.get_by_id(int(patch_filename),
                                     parent=request.patchset)
    if patch is None:
      return respond(request, 'diff_missing.html',
                     {'issue': request.issue,
                      'patchset': request.patchset,
                      'patch': None,
                      'patchsets': request.issue.patchset_set,
                      'filename': patch_filename})
    patch.patchset = request.patchset
    request.patch = patch
    return func(request, *args, **kwds)

  return patch_wrapper


def image_required(func):
  """Decorator that processes the image argument.

  Attributes set on the request:
   content: a Content entity.
  """

  @patch_required
  def image_wrapper(request, image_type, *args, **kwds):
    content = None
    if image_type == "0":
      content = request.patch.content
    elif image_type == "1":
      content = request.patch.patched_content
    # Other values are erroneous so request.content won't be set.
    if not content or not content.data:
      return HttpResponseRedirect(django_settings.MEDIA_URL + "blank.jpg")
    request.mime_type = mimetypes.guess_type(request.patch.filename)[0]
    if not request.mime_type or not request.mime_type.startswith('image/'):
      return HttpResponseRedirect(django_settings.MEDIA_URL + "blank.jpg")
    request.content = content
    return func(request, *args, **kwds)

  return image_wrapper


def json_response(func):
  """Decorator that converts into JSON any returned value that is not an
  HttpResponse. It handles `pretty` URL parameter to tune JSON response for
  either performance or readability."""

  def json_wrapper(request, *args, **kwds):
    data = func(request, *args, **kwds)
    if isinstance(data, HttpResponse):
      return data
    if request.REQUEST.get('pretty','0').lower() in ('1', 'true', 'on'):
      data = json.dumps(data, indent='  ', sort_keys=True)
    else:
      data = json.dumps(data, separators=(',',':'))
    return HttpResponse(data, content_type='application/json; charset=utf-8')

  return json_wrapper
