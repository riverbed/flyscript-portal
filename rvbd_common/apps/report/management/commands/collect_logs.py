# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import optparse

from django.core.management.base import BaseCommand

from rvbd_common.apps.report.utils import create_debug_zipfile


class Command(BaseCommand):
    args = None
    help = 'Clears existing data caches, logs, and optionally application settings.'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--no-summary',
                             action='store_true',
                             dest='no_summary',
                             default=False,
                             help='Do not include summary created from flyscript-about.py'),
    )

    def handle(self, *args, **options):
        fname = create_debug_zipfile(options['no_summary'])
        print 'Zipfile created: %s' % fname
