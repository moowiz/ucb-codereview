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

"""URL mappings for the codereview package."""

# NOTE: Must import *, since Django looks for things here, e.g. handler500.
from django.conf.urls import *  # NOQA
import django.views.defaults

from codereview import feeds

urlpatterns = patterns(
    'codereview.views',
    (r'^$', 'index'),
    (r'^all$', 'all'),
    (r'^bugs$', 'bugs'),
    (r'^mine$', 'mine'),
    (r'^starred$', 'starred'),
    (r'^upload$', 'upload'),
    (r'^(\d+)$', 'show', {}, 'show_bare_issue_number'),
    (r'^(\d+)/(show)?$', 'show'),
    (r'^(\d+)/edit$', 'edit'),
    (r'^(\d+)/publish$', 'publish'),
    (r'^(\d+)/delete$', 'delete'),
    (r'^(\d+)/claim$', 'claim'),
    (r'^(\d+)/release$', 'release'),
    (r'^download/issue(\d+)_(\d+)\.diff', 'download'),
    (r'^download/issue(\d+)_(\d+)_(\d+)\.diff', 'download_patch'),
    (r'^(\d+)/patch/(\d+)/(\d+)$', 'patch'),
    (r'^(\d+)/image/(\d+)/(\d+)/(\d+)$', 'image'),
    (r'^(\d+)/diff/(\d+)/(.+)$', 'diff'),
    (r'^(\d+)/diff2/(\d+):(\d+)/(.+)$', 'diff2'),
    (r'^(\d+)/diff_skipped_lines/(\d+)/(\d+)/(\d+)/(\d+)/([tba])/(\d+)$',
        'diff_skipped_lines'),
    (r'^(\d+)/diff_skipped_lines/(\d+)/(\d+)/$',
        django.views.defaults.page_not_found,
        {}, 'diff_skipped_lines_prefix'),
    (r'^(\d+)/diff2_skipped_lines/(\d+):(\d+)/(\d+)/(\d+)/'
        '(\d+)/([tba])/(\d+)$',
        'diff2_skipped_lines'),
    (r'^(\d+)/diff2_skipped_lines/(\d+):(\d+)/(\d+)/$',
        django.views.defaults.page_not_found,
        {}, 'diff2_skipped_lines_prefix'),
    (r'^(\d+)/upload_content/(\d+)/(\d+)$', 'upload_content'),
    (r'^(\d+)/upload_patch/(\d+)$', 'upload_patch'),
    (r'^(\d+)/upload_complete/(\d+)?$', 'upload_complete'),
    (r'^(\d+)/description$', 'description'),
    (r'^(\d+)/fields', 'fields'),
    (r'^(\d+)/star$', 'star'),
    (r'^(\d+)/unstar$', 'unstar'),
    (r'^(\d+)/draft_message$', 'draft_message'),
    (r'^api/(\d+)/?$', 'api_issue'),
    (r'^api/(\d+)/(\d+)/?$', 'api_patchset'),
    (r'^user/(.+)/delete$', 'account_delete'),
    (r'^user/(.+)/settings$', 'settings'),
    (r'^user/(.+)$', 'show_user'),
    (r'^inline_draft$', 'inline_draft'),
    (r'^user_popup/(.+)$', 'user_popup'),
    (r'^(\d+)/patchset/(\d+)$', 'patchset'),
    (r'^(\d+)/patchset/(\d+)/delete$', 'delete_patchset'),
    (r'^account$', 'account'),
    (r'^use_uploadpy$', 'use_uploadpy'),
    (r'^_ah/mail/(.*)', 'incoming_mail'),
    (r'^xsrf_token$', 'xsrf_token'),
    # patching upload.py on the fly
    (r'^static/upload.py$', 'customized_upload_py'),
    (r'^search$', 'search'),
    (r'^tasks/calculate_delta$', 'calculate_delta'),
    (r'^snippets/add$', 'add_snippet'),
    (r'^snippets/delete/(.+)$', 'delete_snippet'),
    (r'^start_assign_readers$', 'start_assign_readers'),
    (r'^start_migrate_accounts$', 'start_migrate_accounts'),
    (r'^start_get_curr_assigns$', 'start_get_curr_assigns'),

)
