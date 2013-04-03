# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import os
import sys
import time

from django.core.management.base import BaseCommand, CommandError
from django.core import management

from apps.report.models import Report
from project import settings

def import_directory(root):
    """ Recursively imports all python files in a directory
    """
    rootpath = os.path.basename(root)
    for path, dirs, files in os.walk(root):
        for f in files:
            if f.endswith('.pyc') or f == '__init__.py':
                continue
            f = os.path.splitext(f)[0]
            dirpath = os.path.relpath(path, root)
            if dirpath != '.':
                name = os.path.join(rootpath, dirpath, f)
            else:
                name = os.path.join(rootpath, f)
            name = '.'.join(name.split(os.path.sep))
            print 'importing %s as %s' % (f, name)
            __import__(name)


class Command(BaseCommand):
    args = None
    help = 'Reloads the configuration defined in the config directory'

    def handle(self, *args, **options):
        # clear everything
        management.call_command('clean', all=True)
        time.sleep(1)
        management.call_command('syncdb', interactive=False)
        time.sleep(1)
        CONFIG_DIR = os.path.join(settings.PROJECT_ROOT, 'config')
        import_directory(CONFIG_DIR)
