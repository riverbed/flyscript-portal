# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import inspect


def get_request():
    """ Run up the stack and find the `request` object. """
    # XXX see discussion here:
    #    http://nedbatchelder.com/blog/201008/global_django_requests.html
    # alternative would be applying middleware for thread locals
    # if more cases need this behavior, middleware may be better option

    frame = None
    try:
        for f in inspect.stack()[1:]:
            frame = f[0]
            code = frame.f_code
            if code.co_varnames[:1] == ("request",):
                return frame.f_locals["request"]
            elif code.co_varnames[:2] == ("self", "request",):
                return frame.f_locals["request"]
    finally:
        del frame
