import models

from view_decorators import login_required, post_required

from google.appengine.api import memcache

def _get_snippets(request):
  if not models.Account.get_account_for_user(request.user).is_staff:
    # Only staff has access to snippets
    return [], False
  val = memcache.get("snippets")
  if val == None:
    qry = models.Snippet.all()
    val = [snippet for snippet in qry.run()]
    memcache.set("snippets", val)
  return val, True

@login_required
@post_required
def add_snippet(request):
  """
  Adds a snippet to the database. POST request's data should be
  `application/x-www-form-urlencoded` and should have a parameter TEXT
  containing the text of the snippet.
  """
  snippet = models.Snippet(text=db.Text(request.POST.get('text')));
  snippet.put()
  memcache.delete('snippets')
  return HttpResponse()

@login_required
@post_required
def delete_snippet(request, snippet_key):
  """/snippets/delete/<snippet_key>
  Deletes a snippet with SNIPPET_KEY from the database.
  """
  key = db.Key(snippet_key)
  snippet = models.Snippet.get(key)
  snippet.delete()
  memcache.delete('snippets')
  return HttpResponse()