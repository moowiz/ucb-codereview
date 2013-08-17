
from google.appengine.api import users

from django import forms
# Import settings as django_settings to avoid name conflict with settings().
from django.conf import settings as django_settings
from django.utils.safestring import mark_safe

from codereview import models

# Maximum forms fields length
MAX_SUBJECT = 100
MAX_DESCRIPTION = 10000
MAX_URL = 2083
MAX_REVIEWERS = 1000
MAX_CC = 2000
MAX_MESSAGE = 10000
MAX_FILENAME = 255
MAX_DB_KEY_LENGTH = 1000



### Form classes ###

class AccountInput(forms.TextInput):
  # Associates the necessary css/js files for the control.  See
  # http://docs.djangoproject.com/en/dev/topics/forms/media/.
  #
  # Don't forget to place {{formname.media}} into html header
  # when using this html control.
  class Media:
    css = {
      'all': ('http://code.jquery.com/ui/1.10.1/themes/base/jquery-ui.css',)
    }
    js = (
      'http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
      'http://ajax.googleapis.com/ajax/libs/jqueryui/1.10.1/jquery-ui.min.js',
    )

  def render(self, name, value, attrs=None):
    output = super(AccountInput, self).render(name, value, attrs)
    if models.Account.current_user_account is not None:
      # TODO(anatoli): move this into .js media for this form
      data = {'name': name, 
              'multiple': 'true'}
      if self.attrs.get('multiple', True) == False:
        data['multiple'] = 'false'
      data['semester'] = models.Account.current_user_account.semesters[0]
      output += mark_safe(u'''
      <script type="text/javascript">
          $("#id_%(name)s").autocomplete({
          source: function(request, response){
              $.ajax({
                url: "/%(semester)s/account",
                data: {
                    q: request.term,
                    limit: 10,
                },
                success: function(data) {
                    response(data.split("\\n").slice(0, -1));
                }
          } );
      } });
      </script>

              ''' % data)
    return output


class IssueBaseForm(forms.Form):

  subject = forms.CharField(max_length=MAX_SUBJECT,
                            widget=forms.TextInput(attrs={'size': 60}))
  reviewers = forms.CharField(required=False,
                              max_length=MAX_REVIEWERS,
                              widget=AccountInput(attrs={'size': 60}))
  bug_submit = forms.BooleanField(required=False)


class NewForm(IssueBaseForm):

  data = forms.FileField(required=False)
  url = forms.URLField(required=False,
                       max_length=MAX_URL,
                       widget=forms.TextInput(attrs={'size': 60}))
  send_mail = forms.BooleanField(required=False, initial=True)


class AddForm(forms.Form):

  message = forms.CharField(max_length=MAX_SUBJECT,
                            widget=forms.TextInput(attrs={'size': 60}))
  data = forms.FileField(required=False)
  url = forms.URLField(required=False,
                       max_length=MAX_URL,
                       widget=forms.TextInput(attrs={'size': 60}))
  reviewers = forms.CharField(max_length=MAX_REVIEWERS, required=False,
                              widget=AccountInput(attrs={'size': 60}))
  send_mail = forms.BooleanField(required=False, initial=True)


class UploadForm(forms.Form):

  subject = forms.CharField(max_length=MAX_SUBJECT)
  description = forms.CharField(max_length=MAX_DESCRIPTION, required=False)
  content_upload = forms.BooleanField(required=False)
  separate_patches = forms.BooleanField(required=False)
  data = forms.FileField(required=False)
  issue = forms.IntegerField(required=False)
  reviewers = forms.CharField(max_length=MAX_REVIEWERS, required=False)
  send_mail = forms.BooleanField(required=False)
  base_hashes = forms.CharField(required=False)
  repo_guid = forms.CharField(required=False, max_length=MAX_URL)


class UploadContentForm(forms.Form):
  filename = forms.CharField(max_length=MAX_FILENAME)
  status = forms.CharField(required=False, max_length=20)
  checksum = forms.CharField(max_length=32)
  file_too_large = forms.BooleanField(required=False)
  is_binary = forms.BooleanField(required=False)
  is_current = forms.BooleanField(required=False)

  def clean(self):
    # Check presence of 'data'. We cannot use FileField because
    # it disallows empty files.
    super(UploadContentForm, self).clean()
    if not self.files and 'data' not in self.files:
      raise forms.ValidationError, 'No content uploaded.'
    return self.cleaned_data

  def get_uploaded_content(self):
    return self.files['data'].read()


class UploadPatchForm(forms.Form):
  filename = forms.CharField(max_length=MAX_FILENAME)
  content_upload = forms.BooleanField(required=False)

  def get_uploaded_patch(self):
    return self.files['data'].read()

def validate_comp_score(val):
    val = int(val)
    if val < -1 or val > 3:
        raise forms.ValidationError, "Only numbers between -1 and 3 are allowed"

class PublishForm(forms.Form):
  reviewers = forms.CharField(required=False,
                              max_length=MAX_REVIEWERS,
                              widget=AccountInput(attrs={'size': 60}))
  comp_score = forms.IntegerField(required=False, label = 'Composition Score',
           validators=[validate_comp_score])
  bug_submit = forms.BooleanField(required=False)
  send_mail = forms.BooleanField(required=False)
  message = forms.CharField(required=False,
                            max_length=MAX_MESSAGE,
                            widget=forms.Textarea(attrs={'cols': 60}))
  message_only = forms.BooleanField(required=False,
                                    widget=forms.HiddenInput())
  no_redirect = forms.BooleanField(required=False,
                                   widget=forms.HiddenInput())
  in_reply_to = forms.CharField(required=False,
                                max_length=MAX_DB_KEY_LENGTH,
                                widget=forms.HiddenInput())

FORM_CONTEXT_VALUES = [(x, '%d lines' % x) for x in models.CONTEXT_CHOICES]
FORM_CONTEXT_VALUES.append(('', 'Whole file'))


class SettingsForm(forms.Form):

  context = forms.IntegerField(
      widget=forms.Select(choices=FORM_CONTEXT_VALUES),
      required=False,
      label='Context')
  column_width = forms.IntegerField(
      initial=django_settings.DEFAULT_COLUMN_WIDTH,
      min_value=django_settings.MIN_COLUMN_WIDTH,
      max_value=django_settings.MAX_COLUMN_WIDTH)
  sections = forms.CharField(required=False)
  is_staff = forms.BooleanField(required=False)

  def clean_nickname(self):
    nickname = self.cleaned_data.get('nickname')
    # Check for allowed characters
    match = re.match(r'[\w\.\-_\(\) ]+$', nickname, re.UNICODE|re.IGNORECASE)
    if not match:
      raise forms.ValidationError('Allowed characters are letters, digits, '
                                  '".-_()" and spaces.')
    # Check for sane whitespaces
    if re.search(r'\s{2,}', nickname):
      raise forms.ValidationError('Use single spaces between words.')
    if len(nickname) != len(nickname.strip()):
      raise forms.ValidationError('Leading and trailing whitespaces are '
                                  'not allowed.')

    if nickname.lower() == 'me':
      raise forms.ValidationError('Choose a different nickname.')

    # Look for existing nicknames
    accounts = list(models.Account.gql('WHERE lower_nickname = :1',
                                       nickname.lower()))
    for account in accounts:
      if account.key() == models.Account.current_user_account.key():
        continue
      raise forms.ValidationError('This nickname is already in use.')

    return nickname

class SearchForm(forms.Form):

  format = forms.ChoiceField(
      required=False,
      choices=(
        ('html', 'html'),
        ('json', 'json')),
      widget=forms.HiddenInput(attrs={'value': 'html'}))
  keys_only = forms.BooleanField(
      required=False,
      widget=forms.HiddenInput(attrs={'value': 'False'}))
  with_messages = forms.BooleanField(
      required=False,
      widget=forms.HiddenInput(attrs={'value': 'False'}))
  cursor = forms.CharField(
      required=False,
      widget=forms.HiddenInput(attrs={'value': ''}))
  limit = forms.IntegerField(
      required=False,
      min_value=1,
      max_value=1000,
      initial=10,
      widget=forms.HiddenInput(attrs={'value': '10'}))
  closed = forms.NullBooleanField(required=False)
  reviewer = forms.CharField(required=False,
                             max_length=MAX_REVIEWERS,
                             widget=AccountInput(attrs={'size': 60,
                                                        'multiple': False}))
  created_before = forms.DateTimeField(required=False, label='Created before')
  created_after = forms.DateTimeField(
      required=False, label='Created on or after')
  modified_before = forms.DateTimeField(required=False, label='Modified before')
  modified_after = forms.DateTimeField(
      required=False, label='Modified on or after')

  def _clean_accounts(self, key):
    """Cleans up autocomplete field.

    The input is validated to be zero or one name/email and it's
    validated that the users exists.

    Args:
      key: the field name.

    Returns an User instance or raises ValidationError.
    """
    accounts = filter(None,
                      (x.strip()
                       for x in self.cleaned_data.get(key, '').split(',')))
    if len(accounts) > 1:
      raise forms.ValidationError('Only one user name is allowed.')
    elif not accounts:
      return None
    account = accounts[0]
    if '@' in account:
      acct = models.Account.get_account_for_email(account)
    else:
      acct = models.Account.get_account_for_nickname(account)
    if not acct:
      raise forms.ValidationError('Unknown user')
    return acct.user

  def clean_reviewer(self):
    user = self._clean_accounts('reviewer')
    if user:
      return user.email()
