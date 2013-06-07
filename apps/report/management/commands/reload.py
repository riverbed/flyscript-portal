# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import sys
import optparse

from django.core.management.base import BaseCommand, CommandError
from django.core import management

from rvbd.common.exceptions import RvbdHTTPException, RvbdException
from apps.datasource.models import Device
from apps.report.models import Report

from project import settings

# list of files/directories to ignore
IGNORE_FILES = ['helpers']

def import_directory(root, report_name=None, reload_devices=False, ignore_list=None):
    """ Recursively imports all python files in a directory
    """
    if ignore_list is None:
        ignore_list = IGNORE_FILES

    rootpath = os.path.basename(root)
    for path, dirs, files in os.walk(root):
        for f in files:
            if f in ignore_list or not f.endswith('.py') or '__init__' in f:
                continue

            if not reload_devices and f == 'devices.py':
                # check that we have both defined already
                if (Device.objects.filter(module='profiler') and
                        Device.objects.filter(module='shark')):
                    continue

            f = os.path.splitext(f)[0]
            dirpath = os.path.relpath(path, root)
            if dirpath != '.':
                name = os.path.join(rootpath, dirpath, f)
            else:
                name = os.path.join(rootpath, f)
            name = '.'.join(name.split(os.path.sep))

            if report_name and report_name != name:
                print 'skipping %s (%s) ...' % (f, name)
                continue

            try:
                if name in sys.modules:
                    print 'reloading %s as %s' % (f, name)
                    reload(sys.modules[name])
                else:
                    print 'importing %s as %s' % (f, name)
                    __import__(name)

            except RvbdHTTPException as e:
                raise RvbdException, RvbdException('From config file "%s": %s' % (name, e.message)), sys.exc_info()[2]

            except Exception as e:
                if e.message:
                    message = e.message
                else:
                    # SyntaxError has different format
                    message = '%s: (file: %s, line: %s, offset: %s)\n%s' % (e.msg, e.filename, e.lineno, e.offset, e.text)
                raise type(e), type(e)('From config file "%s": %s' % (name, message)), sys.exc_info()[2]


class Command(BaseCommand):
    args = None
    help = 'Reloads the configuration defined in the config directory'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--report-id',
                             action='store',
                             dest='report_id',
                             default=None,
                             help='Reload single report.'),
        optparse.make_option('--reload-devices',
                             action='store_true',
                             dest='reload_devices',
                             default=False,
                             help='Reload device file too (defaults to False).'),
    )

    def handle(self, *args, **options):
        if options['report_id']:
            # single report
            report_name = Report.objects.get(pk=int(options['report_id'])).sourcefile
            management.call_command('clean',
                                    applications=False,
                                    report_id=options['report_id'],
                                    clear_devices=options['reload_devices'])
        else:
            # clear all data
            report_name = None
            management.call_command('clean',
                                    applications=True,
                                    report_id=None,
                                    clear_devices=options['reload_devices'])

        management.call_command('syncdb', interactive=False)
        CONFIG_DIR = os.path.join(settings.PROJECT_ROOT, 'config')
        import_directory(CONFIG_DIR,
                         report_name=report_name,
                         reload_devices=options['reload_devices'])
