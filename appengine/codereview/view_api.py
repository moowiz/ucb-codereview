@issue_required
@json_response
def api_issue(request):
  """/api/<issue> - Gets issue's data as a JSON-encoded dictionary."""
  messages = ('messages' in request.GET and
      request.GET.get('messages').lower() == 'true')
  values = _issue_as_dict(request.issue, messages, request)
  return values


@patchset_required
@json_response
def api_patchset(request):
  """/api/<issue>/<patchset> - Gets an issue's patchset data as a JSON-encoded
  dictionary.
  """
  values = _patchset_as_dict(request.patchset, request)
  return values

@json_response
@handle_year
def search(request):
  """/search - Search for issues or patchset.

  Returns HTTP 500 if the corresponding index is missing.
  """
  if request.method == 'GET':
    form = forms.SearchForm(request.GET, request.semester)
    if not form.is_valid() or not request.GET:
      return respond(request, 'search.html', {'form': form})
  else:
    form = forms.SearchForm(request.POST, request.semester)
    if not form.is_valid():
      return HttpTextResponse('Invalid arguments', status=400)
  # logging.info('%s' % form.cleaned_data)
  keys_only = form.cleaned_data['keys_only'] or False
  format = form.cleaned_data['format'] or 'html'
  limit = form.cleaned_data['limit']
  with_messages = form.cleaned_data['with_messages']
  if format == 'html':
    keys_only = False
    limit = limit or DEFAULT_LIMIT
  else:
    if not limit:
      if keys_only:
        # It's a fast query.
        limit = 1000
      elif with_messages:
        # It's an heavy query.
        limit = 10
      else:
        limit = 100

  q = models.Issue.all(keys_only=keys_only).filter('semester = ', request.semester)
  if form.cleaned_data['cursor']:
    q.with_cursor(form.cleaned_data['cursor'])
  if form.cleaned_data['reviewer']:
    q.filter('reviewers = ', form.cleaned_data['reviewer'])

  # Default sort by ascending key to save on indexes.
  sorted_by = '__key__'
  if form.cleaned_data['modified_before']:
    q.filter('modified < ', form.cleaned_data['modified_before'])
    sorted_by = 'modified'
  if form.cleaned_data['modified_after']:
    q.filter('modified >= ', form.cleaned_data['modified_after'])
    sorted_by = 'modified'
  if form.cleaned_data['created_before']:
    q.filter('created < ', form.cleaned_data['created_before'])
    sorted_by = 'created'
  if form.cleaned_data['created_after']:
    q.filter('created >= ', form.cleaned_data['created_after'])
    sorted_by = 'created'

  q.order(sorted_by)

  # Update the cursor value in the result.
  if format == 'html':
    nav_params = dict(
        (k, v) for k, v in form.cleaned_data.iteritems() if v is not None)
    return _paginate_issues_with_cursor(
        reverse(request, search),
        request,
        q,
        limit,
        'search_results.html',
        extra_nav_parameters=nav_params)

  results = q.fetch(limit)
  form.cleaned_data['cursor'] = q.cursor()
  if keys_only:
    # There's not enough information to filter. The only thing that is leaked is
    # the issue's key.
    filtered_results = results
  else:
    filtered_results = [i for i in results if _can_view_issue(request, i)]
  data = {
    'cursor': form.cleaned_data['cursor'],
  }
  if keys_only:
    data['results'] = [i.id() for i in filtered_results]
  else:
    data['results'] = [_issue_as_dict(i, with_messages, request)
                      for i in filtered_results]
  return data