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

from django.core.management.base import BaseCommand
from django.core import management
from django.core.exceptions import ObjectDoesNotExist

from rvbd.common.exceptions import RvbdHTTPException, RvbdException
from apps.report.models import Report
from apps.devices.devicemanager import DeviceManager

from project import settings

# list of files/directories to ignore
IGNORE_FILES = ['helpers']


class Command(BaseCommand):
    args = None
    help = 'Reloads the configuration defined in the config directory'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--report-id',
                             action='store',
                             dest='report_id',
                             default=None,
                             help='Reload single report.'),

        optparse.make_option('--report-name',
                             action='store',
                             dest='report_name',
                             default=None,
                             help='Reload single report by fully qualified name.'),

        optparse.make_option('--report-dir',
                             action='store',
                             dest='report_dir',
                             default=None,
                             help='Reload reports from this directory.'),
)

    def import_file(self, f, name):
        try:
            if name in sys.modules:
                reload(sys.modules[name])
                self.stdout.write('reloading %s as %s' % (f, name))
            else:
                __import__(name)
                self.stdout.write('importing %s as %s' % (f, name))

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

    def handle(self, *args, **options):
        self.stdout.write('Reloading report objects ... ')

        management.call_command('clean_pyc', path=settings.PROJECT_ROOT)
        management.call_command('syncdb', interactive=False)

        if options['report_id']:
            # single report
            pk = int(options['report_id'])
            report_name = Report.objects.get(pk=pk).sourcefile
            management.call_command('clean',
                                    applications=False,
                                    report_id=options['report_id'],
                                    clear_cache=True,
                                    clear_logs=False)
        elif options['report_name']:
            # single report
            report_name = options['report_name']
            try:
                report_id = Report.objects.get(sourcefile__endswith=report_name).id
                management.call_command('clean',
                                        applications=False,
                                        report_id=report_id,
                                        clear_cache=True,
                                        clear_logs=False)
            except ObjectDoesNotExist:
                pass

            DeviceManager.clear()
            modules = [report_name, 'config.reports.%s' % report_name]
            success = False
            for module in modules:
                try:
                    self.import_file(report_name, module)
                    success = True
                except ImportError:
                    pass
                
            if not success:
                raise ImportError("No module found matching '%s'" % report_name)

            return
        else:
            # clear all data
            report_name = None
            management.call_command('clean',
                                    applications=True,
                                    report_id=None,
                                    clear_cache=True,
                                    clear_logs=False)

        # start with fresh device instances
        DeviceManager.clear()

        report_dir = os.path.join(settings.PROJECT_ROOT, options['report_dir'] or  'config')
            
        self.import_directory(report_dir, report_name=report_name)
