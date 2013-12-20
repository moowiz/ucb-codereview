import models

@post_required
def calculate_delta(request):
  """/calculate_delta - Calculate deltas for a patchset.

  This URL is called by taskqueue to calculate deltas behind the
  scenes. Returning a HttpResponse with any 2xx status means that the
  task was finished successfully. Raising an exception means that the
  taskqueue will retry to run the task.

  This code is similar to the code in _get_patchset_info() which is
  run when a patchset should be displayed in the UI.
  """
  key = request.POST.get('key')
  if not key:
    logging.debug('No key given.')
    return HttpResponse()
  try:
    patchset = models.PatchSet.get(key)
  except (db.KindError, db.BadKeyError), err:
    logging.debug('Invalid PatchSet key %r: %s' % (key, err))
    return HttpResponse()
  if patchset is None:  # e.g. PatchSet was deleted inbetween
    return HttpResponse()
  patchset_id = patchset.key().id()
  patchsets = None
  for patch in patchset.patch_set.filter('delta_calculated =', False):
    if patchsets is None:
      # patchsets is retrieved on first iteration because patchsets
      # isn't needed outside the loop at all.
      patchsets = list(patchset.issue.patchset_set.order('created'))
    patch.delta = _calculate_delta(patch, patchset_id, patchsets)
    patch.delta_calculated = True
    patch.put()
  return HttpResponse()

ASSIGN_READER_BATCH_SIZE = 100
def assign_readers(semester, cursor=None, readers=None, reader_index=0, num_updated=0):
  query = models.Account.all().ancestor(semester).filter('role =', models.ROLE_MAPPING['student'])

  if cursor:
    query.with_cursor(cursor)

  if not readers:
    readers = list(models.Account.all().ancestor(semester).filter('role =', models.ROLE_MAPPING['reader']))

  to_put = []
  for acc in query.fetch(limit=ASSIGN_READER_BATCH_SIZE):
      acc.reader = readers[reader_index]
      reader_index = (reader_index + 1) % len(readers)
      to_put.append(acc)

  if to_put:
      db.put(to_put)
      num_updated += len(to_put)
      logging.debug(
          'Put %d entities to Datastore for a total of %d',
          len(to_put), num_updated)
      # deferred.defer(
      #     assign_readers, semester, cursor=query.cursor(), readers=readers, reader_index=reader_index, num_updated=num_updated)
  else:
      logging.debug(
          'assign_reader complete with %d updates!', num_updated)

@staff_required
def start_assign_readers(request):
  # deferred.defer(assign_readers, request.semester)
  return HttpTextResponse("OK")

TO_COPY = [
  'lower_nickname',
  'stars',
  'default_column_width',
  'default_context',
  'email',
  'user',
]

MIGRATE_BATCH=150

def fix_issues(semester, cursor=None, num_updated=0):
  query = models.Issue.all().filter('semester =', semester.name).filter('subject =', 'proj2')

  if cursor:
    query.with_cursor(cursor)

  to_put = []
  to_iter = list(query.fetch(limit=MIGRATE_BATCH))
  quit = len(to_iter) < MIGRATE_BATCH
  if quit:
    logging.info("Qutting because got {}, less than {}".format(len(to_iter), MIGRATE_BATCH))

  for iss in to_iter:
    accs = [models.Account.get_account_for_email(email) for email in iss.owners]
    accs = [x for x in accs if x]
    to_assign = None
    for acc in accs:
      if acc.reader:
        to_assign = acc.reader
        break
    if not to_assign:
      logging.warn("This issue {} has no readers!".format(iss.key().id()))
    else:
      for acc in accs:
        if not acc.reader or acc.reader.email != to_assign.email:
          acc.reader = to_assign
          to_put.append(acc)

  if not quit:
    db.put(to_put)
    num_updated += len(to_put)
    logging.debug(
        'Put %d entities to Datastore for a total of %d',
        len(to_put), num_updated)
    deferred.defer(
        fix_issues, semester, cursor=query.cursor(), num_updated=num_updated)
  else:
    logging.debug(
        'fix_issues complete with %d updates!', num_updated)

@staff_required
def start_fix_issues(request):
  deferred.defer(fix_issues, request.semester)
  return HttpTextResponse("OK")

def my_put(to_put):
  # print 'putting ', to_put
  real_to_put = [(reader, models.Account.get_account_for_email(email)) for reader, email in to_put]
  for reader, acc in real_to_put:
    acc.reader = reader
  db.put(acc for reader, acc in real_to_put)
  real_to_put = None

def balance_accounts(semester):
  max_acc = models.Account.get_account_for_email('max.alan.wolffe@gmail.com')
  def get_mapping():
    query = models.Account.all(projection=('reader', 'email')).ancestor(semester).filter('role =', 0)
    readers = list(models.Account.all().ancestor(semester).filter('role =', 1))
    reader_mapping = {acc.email.lower():acc for acc in readers}
    mapping = {acc.email.lower():[] for acc in readers}

    for acc in query.run(batch_size=100):
      if acc.reader:
        if acc.reader.email in mapping:
          mapping[acc.reader.email].append(acc.email)
        else:
          logging.warn("reader email {} not found".format(acc.reader.email))
    return mapping, reader_mapping

  mapping, reader_mapping = get_mapping()
  logging.info({k:len(v) for k, v in mapping.iteritems()})
  return

  counts = [len(val) for k, val in mapping.iteritems()]
  mean = int(sum(counts) / len(counts))

  above = []
  below = []

  for k, v in mapping.iteritems():
    if len(v) > mean:
      above.append(v)
    else:
      below.append([k, mean - len(v)])

  to_put = []
  abo = bel = None
  while below and above:
    # print 'below %s above %s' % (below, above)
    bel = (bel if bel and bel[1] else below.pop())
    while bel[1] and above:
      abo = abo or above.pop()
      # print 'abo', abo, 'bel', bel, 'above', above
      while abo and bel[1]:
        it = abo.pop()
        # print 'adding ', it
        to_put.append((reader_mapping[bel[0]], it))
        bel[1] -= 1
    my_put(to_put)
    to_put = None
    to_put = []

  my_put(to_put)

  logging.info({k:len(v) for k, v in get_mapping()[0].iteritems()})


@staff_required
def start_balance(request):
  deferred.defer(balance_accounts, request.semester)
  return HttpTextResponse("OK")

def migrate_accounts(semester):
  def migrate(acc, semester):
    data = {k: getattr(acc, k) for k in TO_COPY}
    data['parent'] = semester
    data['role'] = 2 if acc.is_staff else 0

    acc = models.Account(key_name='<%s>' % data['email'], **data)
    return acc

  semesters = models.Semester.all().fetch(2)
  if semesters[0].key().name():
    bad = semesters[1]
    good = semesters[0]
  else:
    bad = semesters[0]
    good = semesters[1]

  to_put = []
  bad = list(models.Account.all().ancestor(bad))
  for acc in bad:
    to_put.append(migrate(acc, good))

  db.delete(bad)
  db.put(to_put)

@staff_required
def start_migrate_accounts(request):
  # deferred.defer(migrate_accounts, request.semester)
  return HttpTextResponse("OK")

CODE_REVIEW_STUDENTS = [u'asingh820@berkeley.edu', u'alansanders@berkeley.edu', u'mmindanao@berkeley.edu', u'carmen.z@berkeley.edu', u'tta@berkeley.edu', u'shuang@berkeley.edu', u'edward.jl.gao@berkeley.edu', u'lathiata@berkeley.edu', u'spritewu@berkeley.edu', u'esonnad@berkeley.edu', u'jkarstens@berkeley.edu', u'miagilepner@gmail.com', u'elee92@berkeley.edu', u'andymelendez@berkeley.edu', u'sid8795@berkeley.edu', u'hwhuang@berkeley.edu', u'mgandhi93@berkeley.edu', u'aneesh@berkeley.edu', u'timifasubaa@gmail.com', u'jessmchang@berkeley.edu', u'mjr225@berkeley.edu', u'juns123@berkeley.edu', u'junzhucong@gmail.com', u'ajrose@berkeley.edu', u'sapeiris@berkeley.edu', u'daxili@berkeley.edu', u'katelin.bull@gmail.com', u'timothyhongtran@berkeley.edu', u'jooeunlim@berkeley.edu', u'herman121093@berkeley.edu', u'delphine.ho@berkeley.edu', u'mtgibson@berkeley.edu', u'jmahabal@berkeley.edu', u'jenniferhwang@berkeley.edu', u'eandres1@berkeley.edu', u'jenliang@berkeley.edu', u'raeinteymouri@berkeley.edu', u'serenachan@berkeley.edu', u'shannon_wang@berkeley.edu', u'denise.bui@berkeley.edu', u'djhwang423@berkeley.edu', u'kunwoohong@berkeley.edu', u'hly@berkeley.edu', u'sharath3@berkeley.edu', u'stevencheng@berkeley.edu', u'anthonyhbh@gmail.com', u'wangie94@yahoo.com', u'duyhong@berkeley.edu', u'vikramsidhu@berkeley.edu', u'clancyhwang@berkeley.edu', u'stevenhu03@berkeley.edu', u'arjunmehta94@berkeley.edu', u'patransd@berkeley.edu', u'abugni@berkeley.edu', u'xhl0623@berkeley.edu', u'sedward@berkeley.edu', u'abains@berkeley.edu', u'hansong@berkeley.edu', u'sebastian.merz@berkeley.edu', u'sikun.peng@berkeley.edu', u'wj.lin@berkeley.edu', u'vashishtha.mahesh@berkeley.edu', u'charles2299@berkeley.edu', u'amandachow@berkeley.edu', u'jacoblin@berkeley.edu', u'alexerviti@berkeley.edu', u'hr_zhu@berkeley.edu', u'dgoldberg@berkeley.edu', u'dpok@berkeley.edu', u'weisong@berkeley.edu', u'tianshibai@berkeley.edu', u'kyleguo@berkeley.edu', u'pauldubovsky@berkeley.edu', u'patilpranay@berkeley.edu', u'bowenjiang@berkeley.edu', u'hamudabdull@berkeley.edu', u'justinhjiang@berkeley.edu', u'xicong.guan@gmail.com', u'vighnesh.iyer@berkeley.edu', u'dorislee@berkeley.edu', u'achao@berkeley.edu', u'chen.brian@berkeley.edu', u'caobaiyue@berkeley.edu', u'nirshtern@berkeley.edu', u'pitcany@berkeley.edu', u'alcyee@berkeley.edu', u'darksunsets27@gmail.com', u'mjrlee@berkeley.edu', u'morganrconnolly@berkeley.edu', u'hekwan1@berkeley.edu', u'wendydai@berkeley.edu', u'sean.t.loughlin@berkeley.edu', u'jay.iyer@berkeley.edu', u'jhaazpr@berkeley.edu', u'gillguo21@berkeley.edu', u'lcq9501@berkeley.edu', u'chchow@berkeley.edu', u'sau@berkeley.edu', u'hannallee@berkeley.edu']
def get_peer_reviewers(semester):
  return models.Account.get_accounts_for_emails(CODE_REVIEW_STUDENTS)

def get_issues_for_stus(semester, stus, assign):
  iss = [[iss for iss in models.Issue.all().filter('semester = ', semester.name).filter('owners =', stu.email).filter('subject =', assign)] for stu in stus]
  iss = [it for subl in iss for it in subl]
  return list(set(iss))

@staff_required
def start_peer(request):
  deferred.defer(assign_peer_reviewers, request.semester, request.GET.get('assign', 'proj2'))
  return HttpTextResponse("OK")

from random import shuffle

def assign_peer_reviewers(semester, assign, num_reviewers=2):
  stus = get_peer_reviewers(semester)
  to_use = stus[:]
  to_assign = get_issues_for_stus(semester, stus, assign)
  for _ in range(num_reviewers):
    shuffle(to_assign)
    shuffle(to_use)

    i = 0

    # print 'to_use {} to_assign {}'.format(to_use, to_assign)
    while i < len(to_assign):
      using = to_use.pop(0)
      assigning = to_assign.pop(0)

      while using.email in assigning.reviewers or using.email in assigning.owners:
        to_use.append(using)
        using = to_use.pop(0)

      assigning.reviewers.append(using.email)
      to_assign.append(assigning)
      to_use.append(using)

      i += 1

  db.put(to_assign)