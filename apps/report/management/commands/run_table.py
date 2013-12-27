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
import pytz
import sys

from django.core.management.base import BaseCommand, CommandError
from django.forms import ValidationError

from rvbd.common.utils import Formatter
from rvbd.common.timeutils import datetime_to_seconds

from apps.datasource.models import Table, Job, Criteria, CriteriaParameter
from apps.datasource.forms import CriteriaForm
from apps.report.models import Report, Widget

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
        group.add_option('--table-name',
                         action='store',
                         dest='table_name',
                         help='Table name to execute (use --table-list to list all tables)')
        group.add_option('-C', '--criteria',
                         action='append',
                         type='str',
                         dest='criteria',
                         default=None,
                         help='Specify criteria as <key>:<value>, repeat as necessary')
        group.add_option('--criteria-list',
                         action='store_true',
                         dest='criteria_list',
                         default=None,
                         help='List criteria for this table')

        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Run Table Output Options",
                                     "Specify how data should be displayed")
        group.add_option('--csv',
                         action='store_true',
                         dest='as_csv',
                         default=False,
                         help='Output data in CSV format instead of tabular')
        group.add_option('--json',
                         action='store_true',
                         dest='as_json',
                         default=False,
                         help='Output data in JSON format instead of tabular')
        group.add_option('--data',
                         action='store_true',
                         dest='only_data',
                         default=False,
                         help='Output only data ignoring columns')
        group.add_option('--columns',
                         action='store_true',
                         dest='only_columns',
                         default=False,
                         help='Output only columns ignoring data')
        parser.add_option_group(group)
        return parser

    def console(self, msg, ending=None):
        """ Print text to console except if we are writing CSV file """
        if not self.options['as_csv']:
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
        elif options['criteria_list']:
            if 'table_id' in options and options['table_id'] is not None:
                table = Table.objects.get(id=options['table_id'])
            elif 'table_name' in options:
                table = Table.objects.get(name=options['table_name'])
            else:
                raise ValueError("Must specify either --table-id or --table-name to run a table")

            output = [[c.keyword, c.label] for c in table.criteria.all()]
            Formatter.print_table(output, ['Keyword', 'Label'])
        else:
            if 'table_id' in options and options['table_id'] is not None:
                table = Table.objects.get(id=options['table_id'])
            elif 'table_name' in options:
                table = Table.objects.get(name=options['table_name'])
            else:
                raise ValueError("Must specify either --table-id or --table-name to run a table")
                
            # Django gives us a nice error if we can't find the table
            self.console('Table %s found.' % table)

            # Parse critiria options
            criteria_options = {}
            if 'criteria' in options and options['criteria'] is not None:
                for s in options['criteria']:
                    (k,v) = s.split(':', 1)
                    criteria_options[k] = v

            form = CriteriaForm(table.criteria.all(), use_widgets=False,
                                data=criteria_options)
            if not form.is_valid():
                self.console('Invalid criteria:')
                for k,v in form.errors.iteritems():
                    self.console('  %s: %s' % (k,','.join(v)))
                
                sys.exit(1)

            criteria = form.criteria()

            columns = [c.name for c in table.get_columns()]

            if options['only_columns']:
                print columns
                return

            job = Job.create(table=table, criteria=criteria)
            job.save()

            self.console('Job created: %s' % job)
            self.console('Criteria: %s' % criteria.print_details())

            start_time = datetime.datetime.now()
            job.start()
            self.console('Job running . . ', ending='')

            # wait for results
            while not job.done():
                #self.console('. ', ending='')
                #self.stdout.flush()
                time.sleep(1)

            end_time = datetime.datetime.now()
            delta = end_time - start_time
            seconds = float(delta.microseconds + 
                            (delta.seconds + delta.days * 24 * 3600) * 10**6) / 10**6

            self.console('Done!! (elapsed time: %.2f seconds)' % seconds)
            self.console('')

            # Need to refresh the column list in case the job changed them (ephemeral cols)
            columns = [c.name for c in table.get_columns()]

            if job.status == job.COMPLETE:
                if options['as_csv']:
                    Formatter.print_csv(job.values(), columns)
                else:
                    Formatter.print_table(job.values(), columns)
            else:
                self.console("Job completed with an error:")
                self.console(job.message)
                sys.exit(1)
