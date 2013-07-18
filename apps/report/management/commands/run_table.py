# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import time
import datetime
import optparse

from django.core.management.base import BaseCommand, CommandError

from rvbd.common.utils import Formatter

from apps.datasource.models import Table, Job, Criteria
from apps.report.models import Report

# not pretty, but pandas insists on warning about
# some deprecated behavior we really don't care about
# for this script, so ignore them all
import warnings
warnings.filterwarnings("ignore")


class Command(BaseCommand):
    args = None
    help = 'Run a defined table and return results in nice tabular format'

    def create_parser(self, prog_name, subcommand):
        """ Override super version to include special option grouping
        """
        parser = super(Command, self).create_parser(prog_name, subcommand)
        group = optparse.OptionGroup(parser, "Run Table Help",
                                     "Helper commands to display list of tables to run")
        group.add_option('--table-list',
                         action='store_true',
                         dest='table_list',
                         default=False,
                         help='List all available tables by id')
        group.add_option('--table-list-by-report',
                         action='store_true',
                         dest='table_list_by_report',
                         default=False,
                         help='List tables organized by report')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Run Table Criteria",
                                     "Options to specify criteria for specified run table")
        group.add_option('--table-id',
                         action='store',
                         dest='table_id',
                         help='Table ID to execute (use --table-list to find the right ID)')
        group.add_option('--endtime',
                         action='store',
                         dest='endtime',
                         type='float',
                         default=None,
                         help='Criteria: optional, timestamp indicating endtime of report')
        group.add_option('--duration',
                         action='store',
                         dest='duration',
                         type='float',
                         default=None,
                         help='Criteria: optional, minutes for report, overrides default')
        group.add_option('--filterexpr',
                         action='store',
                         dest='filterexpr',
                         default=None,
                         help='Criteria: optional, text filter expression')
        group.add_option('--ignore-cache',
                         action='store_true',
                         dest='ignore_cache',
                         default=False,
                         help='Criteria: optional, if present override any existing caches')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Run Table Output Options",
                                     "Specify how data should be displayed")
        group.add_option('--csv',
                         action='store_true',
                         dest='csv',
                         default=False,
                         help='Output data in CSV format instead of tabular')
        parser.add_option_group(group)
        return parser

    def console(self, msg, ending=None):
        """ Print text to console except if we are writing CSV file """
        if not self.options['csv']:
            self.stdout.write(msg, ending=ending)
            self.stdout.flush()

    def handle(self, *args, **options):
        """ Main command handler
        """
        self.options = options

        if options['table_list']:
            # print out the id's instead of processing anything
            tables = Table.objects.all()
            for t in tables:
                self.console('%5d - %s' % (t.id, t))
        elif options['table_list_by_report']:
            # or print them out organized by report/widget/table
            output = []
            reports = Report.objects.all()
            for report in reports:
                for widget in report.widget_set.all():
                    for table in widget.tables.all():
                        line = [table.id, report.title, widget.title, table]
                        output.append(line)
            Formatter.print_table(output, ['ID', 'Report', 'Widget', 'Table'])
        else:
            table = Table.objects.get(id=options['table_id'])
            # Django gives us a nice error if we can't find the table
            self.console('Table %s found.' % table)

            criteria = Criteria(endtime=options['endtime'],
                                duration=options['duration'],
                                filterexpr=options['filterexpr'],
                                table=table,
                                ignore_cache=options['ignore_cache'])

            job = Job(table=table, criteria=criteria)
            job.save()

            try:
                self.console('Job created: %s' % job)
                self.console('Criteria: %s' % criteria.print_details())

                start_time = datetime.datetime.now()
                job.start()
                self.console('Job running . . ', ending='')

                # wait for results
                while not job.done():
                    self.console('. ', ending='')
                    self.stdout.flush()
                    time.sleep(1)

                end_time = datetime.datetime.now()
                delta = end_time - start_time
                self.console('Done!! (took roughly %.2f seconds)' % delta.total_seconds())
                self.console('')

                columns = [c.name for c in table.get_columns()]
                if not options['csv']:
                    Formatter.print_table(job.data(), columns)
                else:
                    Formatter.print_csv(job.data(), columns)

            finally:
                job.delete()
