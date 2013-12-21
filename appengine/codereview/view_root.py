import models

from view_decorators import handle_year, staff_required, login_required, user_key_required
from view_paginate import _paginate_issues
from view_users import _show_user, _optimize_draft_counts
from view_utils import reverse

from google.appengine.api import memcache

@handle_year
def index(request):
  """/ - Show a list of review issues"""
  if request.user is None:
    return all(request, index_call=True)
  else:
    return mine(request)



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