# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


"""
WSGI config for flyscript-portal.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

"""
import os
import sys
import site

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
os.environ['HOME'] = '/flyscript/wsgi'   # set home directory for wsgi process


# If running under a virtualenv, update these paths, otherwise change to empty
# strings or None
VIRTUALENV_BIN = '/flyscript/virtualenv/bin'
VIRTUALENV_SITE_PACKAGES = '/flyscript/virtualenv/lib/python2.6/site-packages'

if VIRTUALENV_BIN:
    site.addsitedir(VIRTUALENV_SITE_PACKAGES)

    activate_env = os.path.join(VIRTUALENV_BIN, 'activate_this.py')
    execfile(activate_env, dict(__file__=activate_env))

PROJECT_ROOT = '/flyscript/flyscript_portal'
sys.path.append(PROJECT_ROOT)

# Run the WSGI Server
from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()

