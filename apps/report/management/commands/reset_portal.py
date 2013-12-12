# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import glob
import optparse

from django.core.management.base import BaseCommand
from django.core import management

from project import settings

# list of files/directories to ignore
IGNORE_FILES = ['helpers']


class Command(BaseCommand):
    args = None
    help = ('Reset the database. Prompts for confirmation unless '
            '`--force` is included as an argument.')

    option_list = BaseCommand.option_list + (
        optparse.make_option('--force',
                             action='store_true',
                             dest='force',
                             default=False,
                             help='Ignore reset confirmation.'),
    )

    def handle(self, *args, **options):
        if not options['force']:
            msg = ('You have requested to reset portal, this will delete\n'
                   'everything from the database and start from scratch.\n'
                   'Are you sure?\n'
                   "Type 'yes' to continue, or 'no' to cancel: ")
            confirm = raw_input(msg)
        else:
            confirm = 'yes'

        if confirm != 'yes':
            self.stdout.write('Aborting.')
            return

        # lets clear it
        self.stdout.write('Resetting database ... ', ending='')
        management.call_command('reset_db',
                                interactive=False,
                                router='default')
        self.stdout.write('done.')

        management.call_command('clean',
                                applications=False,
                                report_id=None,
                                clear_cache=True,
                                clear_logs=True)

        management.call_command('clean_pyc', path=settings.PROJECT_ROOT)
        management.call_command('syncdb', interactive=False)

        self.stdout.write('Loading initial data ... ', ending='')
        initial_data = glob.glob(os.path.join(settings.PROJECT_ROOT,
                                              'initial_data',
                                              '*.json'))
        management.call_command('loaddata', *initial_data)

        management.call_command('reload', report_id=None)
