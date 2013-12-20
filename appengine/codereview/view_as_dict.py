
def _issue_as_dict(issue, messages, request=None):
  """Converts an issue into a dict."""
  values = {
    'modified': str(issue.modified),
    'created': str(issue.created),
    'reviewers': issue.reviewers,
    'patchsets': [p.key().id() for p in issue.patchset_set.order('created')],
    'subject': issue.subject,
    'issue': issue.key().id(),
  }
  if messages:
    values['messages'] = [
      {
        'sender': m.sender,
        'recipients': m.recipients,
        'date': str(m.date),
        'text': m.text,
        'approval': m.approval,
        'disapproval': m.disapproval,
      }
      for m in models.Message.ancestor(issue)
    ]
  return values

def _patchset_as_dict(patchset, request=None):
  """Converts a patchset into a dict."""
  values = {
    'patchset': patchset.key().id(),
    'issue': patchset.issue.key().id(),
    'message': patchset.message,
    'url': patchset.url,
    'created': str(patchset.created),
    'modified': str(patchset.modified),
    'num_comments': patchset.num_comments,
    'files': {},
  }
  for patch in models.Patch.gql("WHERE patchset = :1", patchset):
    # num_comments and num_drafts are left out for performance reason:
    # they cause a datastore query on first access. They could be added
    # optionally if the need ever arises.
    values['files'][patch.filename] = {
        'id': patch.key().id(),
        'is_binary': patch.is_binary,
        'no_base_file': patch.no_base_file,
        'num_added': patch.num_added,
        'num_chunks': patch.num_chunks,
        'num_removed': patch.num_removed,
        'status': patch.status,
        'property_changes': '\n'.join(patch.property_changes),
    }
  return values