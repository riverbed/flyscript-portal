# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import sys
import traceback

from django.http import HttpResponse, HttpResponseServerError
from django.views import debug
from django.template import Template, RequestContext, loader



class ReloadExceptionClass(debug.ExceptionReporter):
    def get_traceback_html(self):
        t = loader.get_template('error.html')
        #t = Template('error.html', name='Reload Exception')
        c = RequestContext(self.request, self.get_traceback_data())
        return t.render(c)


class ReloadExceptionHandler(object):
    def process_exception(self, request, exception):
        if request.path.startswith('/report/reload'):
            exc_type, exc_value, exc_traceback = sys.exc_info()
            reporter = ReloadExceptionClass(request, exc_type, exc_value, exc_traceback)
            html = reporter.get_traceback_html()
            #return HttpResponseServerError(html, content_type='text/html')
            return HttpResponse(html, content_type='text/html')
