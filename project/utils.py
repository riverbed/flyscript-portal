# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import sys
import inspect

from rvbd.common.exceptions import RvbdHTTPException, RvbdException


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

# list of files/directories to ignore
IGNORE_FILES = ['helpers']


class Importer(object):
    """ Helper functions for importing modules. """
    def __init__(self, buf=None):
        if buf is None:
            self.stdout = sys.stdout
        else:
            self.stdout = buf

    def import_file(self, f, name):
        try:
            if name in sys.modules:
                self.stdout.write('reloading %s as %s' % (f, name))
                reload(sys.modules[name])
            else:
                self.stdout.write('importing %s as %s' % (f, name))
                __import__(name)

        except RvbdHTTPException as e:
            instance = RvbdException('From config file "%s": %s' %
                                     (name, e.message))
            raise RvbdException, instance, sys.exc_info()[2]

        except SyntaxError as e:
            msg_format = '%s: (file: %s, line: %s, offset: %s)\n%s'
            message = msg_format % (e.msg, e.filename,
                                    e.lineno, e.offset, e.text)
            instance = type(e)('From config file "%s": %s' % (name,
                                                              message))
            raise type(e), instance, sys.exc_info()[2]

        except Exception as e:
            instance = type(e)('From config file "%s": %s' % (name,
                                                              str(e)))
            raise type(e), instance, sys.exc_info()[2]

    def import_directory(self, root, report_name=None, ignore_list=None):
        """ Recursively imports all python files in a directory
        """
        if ignore_list is None:
            ignore_list = IGNORE_FILES

        rootpath = os.path.basename(root)
        for path, dirs, files in os.walk(root):
            for i, d in enumerate(dirs):
                if d in ignore_list:
                    dirs.pop(i)

            for f in files:
                if f in ignore_list or not f.endswith('.py') or '__init__' in f:
                    continue

                f = os.path.splitext(f)[0]
                dirpath = os.path.relpath(path, root)
                if dirpath != '.':
                    name = os.path.join(rootpath, dirpath, f)
                else:
                    name = os.path.join(rootpath, f)
                name = '.'.join(name.split(os.path.sep))

                if report_name and report_name != name:
                    self.stdout.write('skipping %s (%s) ...' % (f, name))
                    continue

                self.import_file(f, name)
