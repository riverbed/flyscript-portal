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
from django.db.models import get_app, get_models, Count

from project import settings
from rvbd_portal.apps.report.models import Report, WidgetJob
from rvbd_portal.apps.datasource.models import Table, TableField, Column, Job


class Command(BaseCommand):
    args = None
    help = 'Clears existing data caches, logs, and optionally application settings.'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--applications',
                             action='store_true',
                             dest='applications',
                             default=False,
                             help='Reset all application configurations.'),
        optparse.make_option('--report-id',
                             action='store',
                             dest='report_id',
                             default=None,
                             help='Reload single report instead of all applications.'),
        optparse.make_option('--clear-cache',
                             action='store_true',
                             dest='clear_cache',
                             default=False,
                             help='Clean datacache files.'),
        optparse.make_option('--clear-logs',
                             action='store_true',
                             dest='clear_logs',
                             default=False,
                             help='Delete logs and debug files.'),
    )

    def handle(self, *args, **options):
        if options['clear_cache']:
            # clear cache files
            self.stdout.write('Removing cache files ... ', ending='')
            for f in os.listdir(settings.DATA_CACHE):
                if f != '.gitignore':
                    try:
                        os.unlink(os.path.join(settings.DATA_CACHE, f))
                    except OSError:
                        pass
            self.stdout.write('done.')

        if options['clear_logs']:
            self.stdout.write('Removing debug files ... ', ending='')
            for f in glob.glob(os.path.join(settings.PROJECT_ROOT,
                                            'debug-*.zip')):
                os.remove(f)
            self.stdout.write('done.')

            self.stdout.write('Removing log files ... ', ending='')
            # delete rolled over logs
            for f in glob.glob(os.path.join(settings.PROJECT_ROOT,
                                            'log*.txt.[1-9]')):
                os.remove(f)
            # truncate existing logs
            for f in glob.glob(os.path.join(settings.PROJECT_ROOT,
                                            'log*.txt')):
                with open(f, 'w'):
                    pass
            self.stdout.write('done.')

        if options['applications']:
            # reset objects from main applications
            apps = ['report', 'geolocation', 'datasource', 'console']
            for app in apps:
                for model in get_models(get_app(app)):
                    self.stdout.write('Deleting objects from %s\n' % model)
                    model.objects.all().delete()
        elif options['report_id']:
            # remove Report and its Widgets, Jobs, WidgetJobs, Tables and Columns
            rid = options['report_id']

            def del_table(table):
                Column.objects.filter(table=table.id).delete()
                Job.objects.filter(table=table.id).delete()

                if (table.options is not None) and ('tables' in table.options):
                    for (name, tid) in table.options.tables.items():
                        for deptable in Table.objects.filter(id=int(tid)):
                            del_table(deptable)

                table.delete()

            for section in Report.objects.get(id=rid).section_set.all():
                for widget in section.widget_set.all():
                    for table in widget.tables.all():
                        del_table(table)
                        for wjob in WidgetJob.objects.filter(widget=widget):
                            wjob.delete()
                    widget.delete()

            # Delete all TableFields that are no longer referenced by any Tables or Sections
            (TableField.objects
             .annotate(sections=Count('section'),
                       tables=Count('table'))
             .filter(sections=0, tables=0)
             .delete())
            
            report = Report.objects.get(id=rid)

            report.delete()

        # rotate the logs once
        management.call_command('rotate_logs')
