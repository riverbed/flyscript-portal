# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from re import compile

from django.http import HttpResponseRedirect
from django.conf import settings
from rest_framework.views import exception_handler
from rest_framework.exceptions import NotAuthenticated

from project.utils import get_request


#
# Global authentication locks
# adapted from stack overflow question
# http://tinyurl.com/kaeqg37
#
def get_exempts():
    exempts = [compile(settings.LOGIN_URL.lstrip('/'))]
    if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
        exempts += [compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]
    return exempts


class LoginRequiredMiddleware(object):
    """
    Middleware that requires a user to be authenticated to view any page other
    than reverse(LOGIN_URL_NAME). Exemptions to this requirement can optionally
    be specified in settings via a list of regular expressions in
    LOGIN_EXEMPT_URLS (which you can copy from your urls.py).

    Requires authentication middleware and template context processors to be
    loaded. You'll get an error if they aren't.
    """
    def process_request(self, request):
        assert hasattr(request, 'user'), "The Login Required middleware\
requires authentication middleware to be installed. Edit your\
MIDDLEWARE_CLASSES setting to insert\
'django.contrib.auth.middlware.AuthenticationMiddleware'. If that\
doesn't work, ensure your TEMPLATE_CONTEXT_PROCESSORS setting includes\
'django.core.context_processors.auth'."
        if not request.user.is_authenticated():
            path = request.path.lstrip('/')
            if not any(m.match(path) for m in get_exempts()):
                return HttpResponseRedirect(
                    settings.LOGIN_URL + "?next=" + request.path)


#
# Custom exception handling for Django REST Framework
#
def authentication_exception_handler(exc):
    """ Returns redirect to login page only when requesting HTML. """
    request = get_request()

    if (isinstance(exc, NotAuthenticated) and
            'text/html' in request.negotiator.get_accept_list(request)):
        return HttpResponseRedirect(settings.LOGIN_URL + "?next=" + request.path)

    response = exception_handler(exc)

    return response
