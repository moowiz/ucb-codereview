"""Configuration."""

import logging
import os
import re

from google.appengine.ext.appstats import recording

logging.info('Loading %s from %s', __name__, __file__)

# Custom webapp middleware to add Appstats.
def webapp_add_wsgi_middleware(app):
  app = recording.appstats_wsgi_middleware(app)
  return app


# Segregate Appstats by runtime (python vs. python27).
appstats_KEY_NAMESPACE = '__appstats_%s__' % os.getenv('APPENGINE_RUNTIME')

# Django 1.2+ requires DJANGO_SETTINGS_MODULE environment variable to be set
# http://code.google.com/appengine/docs/python/tools/libraries.html#Django 
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
# NOTE: All "main" scripts must import webapp.template before django.

