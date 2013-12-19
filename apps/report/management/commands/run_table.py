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

from apps.datasource.models import Table, Job, Criteria, TableCriteria
from apps.report.models import Report, Widget
from apps.report.forms import create_report_criteria_form

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
        group.add_option('--endtime',
                         action='store',
                         dest='endtime',
                         type='str',
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
        group.add_option('--criteria',
                         action='append',
                         type='str',
                         dest='criteria',
                         default=None,
                         help='Criteria: optional, custome criteria <key>:<value>')

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
        else:
            if 'table_id' in options and options['table_id'] is not None:
                table = Table.objects.get(id=options['table_id'])
            elif 'table_name' in options:
                table = Table.objects.get(name=options['table_name'])
            else:
                raise ValueError("Must specify either --table-id or --table-name to run a table")
                
            # Django gives us a nice error if we can't find the table
            self.console('Table %s found.' % table)

            # Look for a related report
            widgets = Widget.objects.filter(tables__in=[table])
            if len(widgets) > 0:
                report = widgets[0].report
                form = create_report_criteria_form(report=report)
            else:
                form = None

            add_options = {}
            if 'criteria' in options and options['criteria'] is not None:
                for s in options['criteria']:
                    (k,v) = s.split(':', 1)
                    add_options[k] = v

            if 'endtime' in options and options['endtime'] is not None:
                try:
                    endtime = form.fields['endtime'].clean(options['endtime'])
                except ValidationError:
                    raise ValidationError("Could not parse endtime: %s, try MM/DD/YYYY HH:MM am" % options['endtime'])
                tz = pytz.timezone("US/Eastern")
                endtime = endtime.replace(tzinfo=tz)
            else:
                endtime = datetime.datetime.now()

            criteria = Criteria(endtime=datetime_to_seconds(endtime),
                                duration=options['duration'],
                                filterexpr=options['filterexpr'],
                                table=table,
                                ignore_cache=options['ignore_cache'])


            if form:
                for k,field in form.fields.iteritems():
                    if not k.startswith('criteria_'): continue

                    tc = TableCriteria.objects.get(pk=k.split('_')[1])

                    if (  options['criteria'] is not None and
                          tc.keyword in add_options):
                        val = add_options[tc.keyword]
                    else:
                        val = field.initial

                    # handle table criteria and generate children objects
                    tc = TableCriteria.get_instance(k, val) 
                    criteria[k] = tc
                    for child in tc.children.all():
                        child.value = val
                        criteria['criteria_%d' % child.id] = child

            columns = [c.name for c in table.get_columns()]

            if options['only_columns']:
                print columns
                return

            job = Job(table=table, criteria=criteria)
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
