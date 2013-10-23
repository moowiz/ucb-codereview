# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Django template library for Rietveld."""

import cgi
import settings
import logging

from google.appengine.api import memcache
from google.appengine.api import users

import django.template
import django.utils.safestring
from django.core.urlresolvers import reverse

from codereview import models

register = django.template.Library()

user_cache = {}


def get_links_for_users(user_emails):
  """Return a dictionary of email->link to user page"""
  link_dict = {}

  # initialize with email usernames
  for email in user_emails:
    nick = email.split('@', 1)[0]
    link_dict[email] = cgi.escape(nick)

  curr_acc = models.Account.get_account_for_user(users.get_current_user())
  accounts = models.Account.get_accounts_for_emails(user_emails)
  semester = curr_acc.parent().name

  for account in accounts:
    if account:
      nick = cgi.escape(account.nickname)
      if curr_acc.is_staff or account.is_staff:
        ret = ('<a href="%s" onMouseOver="M_showUserInfoPopup(this)">%s</a>' %
              (reverse('codereview.views.show_user', args=[semester, account.nickname]),
              nick))
        link_dict[account.email] = ret
      else:
        link_dict[account.email] = get_nickname(account, curr_acc=curr_acc)

  return link_dict

def _get_info(email):
  key = '<%s>:staff'
  val = memcache.get(key)
  if not val:
    val = models.Account.get_account_for_email(email).is_staff
    memcache.set(key, val, time=21600) # 6 hours
  return email, val

def get_nickname(email_or_acc_to_show, never_me=False, curr_acc=None):
  """Return a nickname for an email address.

  If 'never_me' is True, 'me' is not returned if 'email' belongs to the
  current logged in user. 
  """

  if not curr_acc:
    curr_acc = models.Account.current_user_account

  if not curr_acc:
    curr_acc_email, curr_staff = _get_info(users.get_current_user().email())
  else:
    curr_acc_email, curr_staff = curr_acc.email, curr_acc.is_staff

  if isinstance(email_or_acc_to_show, models.Account):
    acc_to_show_email = email_or_acc_to_show.email
    acc_to_show_staff = email_or_acc_to_show.is_staff
  else:
    if isinstance(email_or_acc_to_show, users.User):
      email_or_acc_to_show = email_or_acc_to_show.email()

    email = str(email_or_acc_to_show)
    acc_to_show_email, acc_to_show_staff = _get_info(email)
    assert type(email) is str, "ERR: type of email is %s" % str(type(email))

  if not never_me:
    if acc_to_show_email == curr_acc_email:
      return 'me'

  if _can_see_other_user(curr_acc_email, acc_to_show_email, curr_staff, acc_to_show_staff):
    return acc_to_show_email[:acc_to_show_email.find('@')]
  else:
    return "Anonymous"

def _can_see_other_user(curr_email, other_email, curr_staff, other_staff):
  issue = models.Issue.current_issue

  if curr_email == other_email:
    return True
  if curr_staff or other_staff:
    return True
  if not issue:
    return False
  other_acc_is_owner = other_email in issue.owners
  curr_acc_is_owner = curr_email in issue.owners
  rval = not other_acc_is_owner ^ curr_acc_is_owner
  # print 'returning {} for other {} and curr {} owners {}'.format(rval, other_email.email, curr_acc.email, issue.owners)
  return rval

def get_link_for_user(email):
  """Get a link to a user's profile page."""
  links = get_links_for_users([email])
  return links[email]

class UrlTemplateNode(django.template.Node):
  def __init__(self, url, args):
    super(UrlTemplateNode, self).__init__()
    self.url = url
    self.args = [django.template.Variable(x) for x in args]

  def render(self, context):
    return reverse(self.url, args=[context['semester'].name] + [x.resolve(context) for x in self.args])

@register.tag
def url(parser, token):
  to_use = token.split_contents()
  return UrlTemplateNode(to_use[1], to_use[2:])

@register.filter
def show_user(email, issue=None, _autoescape=None, _memcache_results=None):
  """Render a link to the user's dashboard, with text being the nickname."""
  if isinstance(email, users.User):
    email = email.email()

  user = users.get_current_user()
  if user is not None and email == user.email():
    return 'me'

  if issue:
    models.Issue.current_issue = issue

  ret = get_link_for_user(email)

  return django.utils.safestring.mark_safe(ret)


@register.filter
def show_users(email_list, issue=None):
  """Render list of links to each user's dashboard."""
  new_email_list = []
  for email in email_list:
    if isinstance(email, users.User):
      email = email.email()
    new_email_list.append(email)

  if issue:
    models.Issue.current_issue = issue

  links = get_links_for_users(new_email_list)

  user = users.get_current_user()
  if user is not None:
    links[user.email()] = 'me'

  return django.utils.safestring.mark_safe(', '.join(
      links[email] for email in email_list))


class UrlAppendViewSettingsNode(django.template.Node):
  """Django template tag that appends context and column_width parameter.

  This tag should be used after any URL that requires view settings.

  Example:

    <a href='{%url /foo%}{%urlappend_view_settings%}'>

  The tag tries to get the current column width and context from the
  template context and if they're present it returns '?param1&param2'
  otherwise it returns an empty string.
  """

  def __init__(self):
    super(UrlAppendViewSettingsNode, self).__init__()
    self.view_context = django.template.Variable('context')
    self.view_colwidth = django.template.Variable('column_width')

  def render(self, context):
    """Returns a HTML fragment."""
    url_params = []

    current_context = -1
    try:
      current_context = self.view_context.resolve(context)
    except django.template.VariableDoesNotExist:
      pass
    if current_context is None:
      url_params.append('context=')
    elif isinstance(current_context, int) and current_context > 0:
      url_params.append('context=%d' % current_context)

    current_colwidth = None
    try:
      current_colwidth = self.view_colwidth.resolve(context)
    except django.template.VariableDoesNotExist:
      pass
    if current_colwidth is not None:
      url_params.append('column_width=%d' % current_colwidth)

    if url_params:
      return '?%s' % '&'.join(url_params)
    return ''

@register.tag
def urlappend_view_settings(_parser, _token):
  """The actual template tag."""
  return UrlAppendViewSettingsNode()



class NicknameNode(django.template.Node):
  """Renders a nickname for a given email address.

  The return value is cached if a HttpRequest is available in a
  'request' template variable.

  The template tag accepts one or two arguments. The first argument is
  the template variable for the email address. If the optional second
  argument evaluates to True, 'me' as nickname is never rendered.

  Example usage:
    {% cached_nickname msg.sender %}
    {% cached_nickname msg.sender True %}
  """

  def __init__(self, email_address, never_me=''):
    """Constructor.
    'email_address' is the name of the template variable that holds an
    email address. If 'never_me' evaluates to True, 'me' won't be returned.
    """
    super(NicknameNode, self).__init__()
    self.email_address = django.template.Variable(email_address)
    self.never_me = bool(never_me.strip())
    self.is_multi = False

  def render(self, context):
    try:
      email = self.email_address.resolve(context)
    except django.template.VariableDoesNotExist:
      return ''
    if self.is_multi:
      return ', '.join(get_nickname(e, self.never_me) for e in email)
    return get_nickname(email, self.never_me)


@register.tag
def nickname(_parser, token):
  """Almost the same as nickname filter but the result is cached."""
  try:
    _, email_address, never_me = token.split_contents()
  except ValueError:
    try:
      _, email_address = token.split_contents()
      never_me = ''
    except ValueError:
      raise django.template.TemplateSyntaxError(
        "%r requires exactly one or two arguments" % token.contents.split()[0])
  return NicknameNode(email_address, never_me)

@register.tag
def nicknames(parser, token):
  """Wrapper for nickname tag with is_multi flag enabled."""
  node = nickname(parser, token)
  node.is_multi = True
  return node
