# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import sys
import time
import optparse

from django.core.management.base import BaseCommand, CommandError

from rvbd.common.utils import Formatter

from apps.datasource.models import Table, Job, Criteria

# not pretty, but pandas insists on warning about
# some deprecated behavior we really don't care about
# for this script, so ignore them all
import warnings
warnings.filterwarnings("ignore")

class Command(BaseCommand):
    args = None
    help = 'Run a defined table and return results in nice tabular format'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--table-list',
                             action='store_true',
                             dest='table_list',
                             default=False,
                             help='List all available tables by id'),
        optparse.make_option('--table-id',
                             action='store',
                             dest='table_id',
                             help='Table ID to execute (use --table-list to find the right ID)'),
        optparse.make_option('--endtime',
                             action='store',
                             dest='endtime',
                             type='float',
                             default=None,
                             help='Criteria: optional, timestamp indicating endtime of report'),
        optparse.make_option('--duration',
                             action='store',
                             dest='duration',
                             type='float',
                             default=None,
                             help='Criteria: optional, minutes for report, overrides default'),
        optparse.make_option('--filterexpr',
                             action='store',
                             dest='filterexpr',
                             default=None,
                             help='Criteria: optional, text filter expression'),
        optparse.make_option('--ignore-cache',
                             action='store_true',
                             dest='ignore_cache',
                             default=False,
                             help='Criteria: optional, if present override any existing caches'),
    )

    def handle(self, *args, **options):

        if options['table_list']:
            # print out the id's instead of processing anything
            tables = Table.objects.all()
            for t in tables:
                print '%5d - %s' % (t.id, t)
        else:
            table = Table.objects.get(id=options['table_id'])
            # Django gives us a nice error if we can't find the table
            print 'Table %s found.' % table

            criteria = Criteria(endtime=options['endtime'],
                                duration=options['duration'],
                                filterexpr=options['filterexpr'],
                                table=table,
                                ignore_cache=options['ignore_cache'])

            job = Job(table=table, criteria=criteria)
            job.save()

            try:
                print 'Job created: %s' % job
                print 'Criteria: %s' % criteria.print_details()

                job.start()
                print 'Job running . .',

                # wait for results
                while not job.done():
                    print '.',
                    sys.stdout.flush()
                    time.sleep(1)

                print 'Done!!'
                print ''

                columns = [c.name for c in table.get_columns()]
                Formatter.print_table(job.data(), columns)
            finally:
                job.delete()
