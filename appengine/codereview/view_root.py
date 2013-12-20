from view_decorators import handle_year
from view_paginate import _paginate_issues

@handle_year
def index(request):
  """/ - Show a list of review issues"""
  if request.user is None:
    return all(request, index_call=True)
  else:
    return mine(request)


DEFAULT_LIMIT = 50


def _url(path, **kwargs):
  """Format parameters for query string.

  Args:
    path: Path of URL.
    kwargs: Keyword parameters are treated as values to add to the query
      parameter of the URL.  If empty no query parameters will be added to
      path and '?' omitted from the URL.
  """
  if kwargs:
    encoded_parameters = urllib.urlencode(kwargs)
    if path.endswith('?'):
      # Trailing ? on path.  Append parameters to end.
      return '%s%s' % (path, encoded_parameters)
    elif '?' in path:
      # Append additional parameters to existing query parameters.
      return '%s&%s' % (path, encoded_parameters)
    else:
      # Add query parameters to path with no query parameters.
      return '%s?%s' % (path, encoded_parameters)
  else:
    return path



@staff_required
def bugs(request):
  """/bugs - Show a list of open bug submits"""
  query = models.Issue.all()
  query.filter('bug =', True)
  query.order('-modified')
  query.order('bug_owner')

  return _paginate_issues(reverse(request, bugs),
                          request,
                          query,
                          'bugs.html')

def last_modified_issue(request):
  last = memcache.get('l_iss')
  if not last:
    last = models.Issue.all().order('-modified')

    if request.closed:
      last = last.filter('closed =', request.closed)
    last = last.fetch(1)

    if last:
      last = last[0].modified
    else:
      last = datetime.datetime(2013, 1, 1)
    memcache.set('l_iss', last)
  last = datetime.datetime(2013, 1, 1)
  return last

def clean_args_all(func):
  def wrapper(request, index_call=False):
    closed = request.GET.get('closed', '')
    if closed in ('0', 'false'):
      closed = False
    elif closed in ('1', 'true'):
      closed = True
    elif index_call:
      # for index we display only open issues by default
      closed = False
    else:
      closed = None

    request.closed = closed

    return func(request)
  return wrapper

@staff_required
@clean_args_all
def all(request):
  """/all - Show a list of up to DEFAULT_LIMIT recent issues."""
  closed = request.closed

  key = 'all'
  if closed is not None:
    key += '.c' if closed else '.o'
  if 'offset' in request.GET or 'limit' in request.GET:
    key = None
  val = memcache.get(key) if key else None
  val = None
  if not val:
    nav_parameters = {}
    if closed is not None:
      nav_parameters['closed'] = int(closed)

    query = models.Issue.all().filter('semester =', request.semester.name)
    if closed is not None:
      # return only opened or closed issues
      query.filter('closed =', closed)
    query.order('-modified')

    val = _paginate_issues(reverse(request, all),
                            request,
                            query,
                            'all.html',
                            extra_nav_parameters=nav_parameters,
                            extra_template_params={'closed':closed})
    if key:
      memcache.set(key, val)
  return val

def _optimize_draft_counts(issues):
  """Force _num_drafts to zero for issues that are known to have no drafts.

  Args:
    issues: list of model.Issue instances.

  This inspects the drafts attribute of the current user's Account
  instance, and forces the draft count to zero of those issues in the
  list that aren't mentioned there.

  If there is no current user, all draft counts are forced to 0.
  """
  if not issues:
    return

  account = models.Account.current_user_account
  if account is None:
    issue_ids = None
  else:
    issue_ids = account.drafts
  for issue in issues:
    if issue_ids is None or issue.key().id() not in issue_ids:
      issue._num_drafts = 0


@login_required
def mine(request):
  """/mine - Show a list of issues created by the current user."""
  request.user_to_show = request.user
  return _show_user(request)

@login_required
@user_key_required
def show_user(request):
  """/user - Show the user's dashboard"""
  return _show_user(request)