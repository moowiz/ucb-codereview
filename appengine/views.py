from django import forms
# Import settings as django_settings to avoid name conflict with settings().
from django.conf import settings as django_settings
from django.shortcuts import redirect

def redirect_to_current_semester(request):
	return redirect('/' + django_settings.CURRENT_SEMESTER + "/")