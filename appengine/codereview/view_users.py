
def _show_user(request):
  user_to_show = request.user_to_show
  acc = models.Account.get_account_for_user(request.user)
  acc_to_show = models.Account.get_account_for_user(user_to_show)
  if not acc.is_staff:
    if user_to_show != request.user:
      return HttpTextResponse("You do not have permission to view this user", status=403)
    if request.semester.name != acc_to_show.parent().name:
      return HttpTextResponse("You do not have permission to view a user in this semester", status=403)

  if user_to_show == request.user:
    query = models.Comment.all().filter('draft =', True)
    query = query.filter('author =', request.user).fetch(100)
    draft_keys = set(d.parent_key().parent().parent() for d in query)
    draft_issues = models.Issue.get(draft_keys)
  else:
    draft_issues = draft_keys = []

  get_assign = request.GET.get('assign', None)
  def make_query(assign=None):
    query = models.Issue.all().filter('semester =', request.semester.name)
    if not assign:
      assign = get_assign

    if assign:
      query.filter('subject =', assign)
    query.order('-modified')
    return query

  if acc_to_show.is_staff:
    if acc_to_show.role == models.ROLE_MAPPING['reader']:
      emails = set(acc.email for acc in models.get_accounts_for_reader(acc_to_show, request.semester))
      all_issues = ()
      all_queries = tuple(tuple(((email, subj), make_query(subj).filter('owners =', email).run()) for subj in models.VALID_SUBJECTS) for email in emails)
      all_queries = tuple(it for subl in all_queries for it in subl)

      mapping = collections.defaultdict(dict)
      for (email, subj), query in all_queries:
        if email not in mapping[subj]:
          to_add = tuple(query)
          for iss in to_add:
            for em in iss.owners:
              mapping[subj][em] = True

          all_issues += to_add

      all_issues = tuple(issue for issue in all_issues if _can_view_issue(request, issue))

    elif acc.role == models.ROLE_MAPPING['ta']:
      all_issues = ()
    else:
      return HttpTextResponse("Weird settings....", status=403)

    others_issues = others_open = others_closed = ()
  else:
    query = make_query().filter('owners =', user_to_show.email().lower())
    all_issues = tuple(issue for issue in query if _can_view_issue(request, issue))

    query = make_query().filter('reviewers =', user_to_show.email().lower())
    others_issues = tuple(issue for issue in query if _can_view_issue(request, issue))
    others_closed = ()
    others_open = ()
    for iss in others_issues:
      if iss.closed:
        others_closed += (iss,)
      else:
        others_open += (iss,)

  review_issues = ()
  closed_issues = ()
  for iss in all_issues:
      if iss.closed:
          closed_issues += (iss,)
      else:
          review_issues += (iss,)

  for lst in (all_issues, others_issues):
    _load_users_for_issues(lst)
    _optimize_draft_counts(lst)

  return respond(request, 'user.html',
                 {'email': user_to_show.email(),
                  'review_issues': review_issues,
                  'closed_issues': closed_issues,
                  'others_open': others_open,
                  'others_closed': others_closed,
                  'draft_issues': draft_issues,
                  })

### User Profiles ###

@user_key_required
@login_required
@xsrf_required
def settings(request):
  account = models.Account.get_account_for_user(request.user_to_show)
  tmp_acc = models.Account.current_user_account
  if not (tmp_acc.is_staff or tmp_acc == account):
      return HttpTextResponse("Error: Unable to edit settings for this user", status=404)
  if request.method != 'POST':
    nickname = account.nickname
    default_context = account.default_context
    default_column_width = account.default_column_width
    role = models.REV_ROLE_MAPPING[account.role]
    if account.reader:
      reader = account.reader.email
    else:
      reader = ''
    form = forms.SettingsForm(initial={'nickname': nickname,
                                 'context': default_context,
                                 'column_width': default_column_width,
                                 'role': role,
                                 'reader': reader,
                                 })
    if not request.is_staff:
      del form.fields['role']
      del form.fields['reader']

    return respond(request, "settings.html", {'form':form,
                                              'user_to_show': request.user_to_show,})
  form = forms.SettingsForm(request.POST)
  if not form.is_valid():
    return HttpResponseRedirect(reverse(request, mine))
  data = form.cleaned_data
  account.default_context = data.get('context')
  account.default_column_width = data.get('column_width')
  if 'role' in data:
      account.role = data['role']
      #TODO make sure this is staff doing this
  if 'reader' in data:
    account.reader = data['reader']
  account.put()
  return HttpResponseRedirect(reverse(request, show_user, args=(request.user_to_show,)))


@user_key_required
@login_required
@xsrf_required
def account_delete(request):
  request_acc = models.Account.get_account_for_user(request.user)
  if not (request_acc.is_staff or request.user == request.user_to_show):
      return HttpTextResponse("Invalid permissions to delete this user", status=403)
  account = models.Account.get_account_for_user(request.user_to_show)
  account.delete()
  return HttpResponseRedirect(users.create_logout_url(reverse(request, index)))


@user_key_required
def user_popup(request):
  """/user_popup - Pop up to show the user info."""
  try:
    return _user_popup(request)
  except Exception, err:
    logging.exception('Exception in user_popup processing:')
    # Return HttpResponse because the JS part expects a 200 status code.
    return HttpHtmlResponse(
        '<font color="red">Error: %s; please report!</font>' %
        err.__class__.__name__)


def _user_popup(request):
  user = request.user_to_show
  popup_html = memcache.get('user_popup:' + user.email())
  if popup_html is None:
    num_issues_reviewed = db.GqlQuery(
      'SELECT * FROM Issue '
      'WHERE closed = FALSE AND reviewers = :1',
      user.email()).count()

    user.nickname = models.Account.get_nickname_for_email(user.email())
    popup_html = render_to_response('user_popup.html',
                            {'user': user,
                             'num_issues_reviewed': num_issues_reviewed,
                             },
                             context_instance=RequestContext(request))
    # Use time expired cache because the number of issues will change over time
    memcache.add('user_popup:' + user.email(), popup_html, 60)
  return popup_html

@login_required
def xsrf_token(request):
  """/xsrf_token - Return the user's XSRF token.

  This is used by tools like git-cl that need to be able to interact with the
  site on the user's behalf.  A custom header named X-Requesting-XSRF-Token must
  be included in the HTTP request; an error is returned otherwise.
  """
  if not request.META.has_key('HTTP_X_REQUESTING_XSRF_TOKEN'):
    return HttpTextResponse(
        'Please include a header named X-Requesting-XSRF-Token '
        '(its content doesn\'t matter).',
        status=400)
  return HttpTextResponse(models.Account.current_user_account.get_xsrf_token())