import os

import models

from django.http import HttpResponse

IS_DEV = os.environ['SERVER_SOFTWARE'].startswith('Dev')  # Development server

def reverse(request, url, *args, **kwds):
  _args = kwds.pop('args', [])
  if type(_args) is tuple:
    _args = (request.semester.name,) + _args
  else:
    _args.insert(0, request.semester.name)
  kwds['args'] = _args
  return _reverse(url, *args, **kwds)


### Exceptions ###
class InvalidIncomingEmailError(Exception):
  """Exception raised by incoming mail handler when a problem occurs."""


### Helper functions ###

def respond(request, template, params=None):
  """Helper to render a response, passing standard stuff to the response.

  Args:
    request: The request object.
    template: The template name; '.html' is appended automatically.
    params: A dict giving the template parameters; modified in-place.

  Returns:
    Whatever render_to_response(template, params) returns.

  Raises:
    Whatever render_to_response(template, params) raises.
  """
  if params is None:
    params = {}
  if request.user is not None:
    account = models.Account.current_user_account
  params['request'] = request
  params['user'] = request.user
  params['semester'] = getattr(request, 'semester', '')
  if request.user:
    params['user_id'] = request.user.user_id
  params['bug_owner'] = request.issue.bug_owner if hasattr(request, 'issue') else None
  params['is_admin'] = request.user_is_admin
  params['is_staff'] = request.user and account.is_staff
  params['is_dev'] = IS_DEV
  params['media_url'] = django_settings.MEDIA_URL
  params['special_banner'] = getattr(django_settings, 'SPECIAL_BANNER', None)
  full_path = request.get_full_path().encode('utf-8')
  if request.user is None:
    params['sign_in'] = users.create_login_url(full_path)
  else:
    params['sign_out'] = users.create_logout_url(full_path)
    account = models.Account.current_user_account
    if account is not None:
      params['xsrf_token'] = account.get_xsrf_token()
  params['rietveld_revision'] = django_settings.RIETVELD_REVISION
  try:
    return render_to_response(template, params,
                              context_instance=RequestContext(request))
  finally:
    library.user_cache.clear() # don't want this sticking around


def _random_bytes(n):
  """Helper returning a string of random bytes of given length."""
  return ''.join(map(chr, (random.randrange(256) for i in xrange(n))))


def _clean_int(value, default, min_value=None, max_value=None):
  """Helper to cast value to int and to clip it to min or max_value.

  Args:
    value: Any value (preferably something that can be casted to int).
    default: Default value to be used when type casting fails.
    min_value: Minimum allowed value (default: None).
    max_value: Maximum allowed value (default: None).

  Returns:
    An integer between min_value and max_value.
  """
  if not isinstance(value, (int, long)):
    try:
      value = int(value)
    except (TypeError, ValueError):
      value = default
  if min_value is not None:
    value = max(min_value, value)
  if max_value is not None:
    value = min(value, max_value)
  return value


def _can_view_issue(request, issue):
  user = request.user
  if models.Account.get_account_for_user(user).is_staff:
    return True
  if issue.semester != request.semester.name:
    return False
  user_email = user.email().lower()
  return (user_email in issue.reviewers or user_email in issue.owners)


class HttpTextResponse(HttpResponse):
  def __init__(self, *args, **kwargs):
    kwargs['content_type'] = 'text/plain; charset=utf-8'
    super(HttpTextResponse, self).__init__(*args, **kwargs)


class HttpHtmlResponse(HttpResponse):
  def __init__(self, *args, **kwargs):
    kwargs['content_type'] = 'text/html; charset=utf-8'
    super(HttpHtmlResponse, self).__init__(*args, **kwargs)

