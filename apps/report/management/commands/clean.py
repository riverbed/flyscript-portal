# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import os
import optparse

from django.core.management.base import BaseCommand
from django.core import management
from django.db.models import get_app, get_models

from project import settings
from apps.report.models import Report, Widget, WidgetJob
from apps.devices.devicemanager import DeviceManager
from apps.datasource.models import Table, Column, Job


class Command(BaseCommand):
    args = None
    help = 'Clears existing data caches, logs, and optionally application settings.'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--applications',
                             action='store_true',
                             dest='applications',
                             default=False,
                             help='Reset application configurations.'),
        optparse.make_option('--report-id',
                             action='store',
                             dest='report_id',
                             default=None,
                             help='Reload single report instead of all applications.'),
        optparse.make_option('--clear-devices',
                             action='store_true',
                             dest='clear_devices',
                             default=False,
                             help='Reload device file too (defaults to False).'),
    )

    def handle(self, *args, **options):
        # clear cache files
        for f in os.listdir(settings.DATA_CACHE):
            if f != '.gitignore':
                try:
                    os.unlink(os.path.join(settings.DATA_CACHE, f))
                except OSError:
                    pass

        # rotate the logs once
        management.call_command('rotate_logs')

        # reset database, keeping devices
        if options['applications']:
            apps = ['report', 'geolocation', 'datasource', 'console']
            for app in apps:
                for model in get_models(get_app(app)):
                    print 'Deleting objects from %s' % model
                    model.objects.all().delete()
        elif options['report_id']:
            # remove Report and its Widgets, Jobs, WidgetJobs, Tables and Columns
            rid = options['report_id']

            def del_table(table):
                for column in Column.objects.filter(table=table.id):
                    column.delete()
                for job in Job.objects.filter(table=table.id):
                    job.delete()

                if (table.options is not None) and ('tables' in table.options):
                    for (name, tid) in table.options.tables.items():
                        for deptable in Table.objects.filter(id=int(tid)):
                            del_table(deptable)

                for criteria in table.criteria.all():
                    # try to delete only TableCriteria where this
                    # table was the last reference
                    if len(criteria.table_set.all()) == 1:
                        criteria.delete()

                table.delete()
                
            for widget in Widget.objects.filter(report=rid):
                for table in widget.tables.all():
                    del_table(table)
                for wjob in WidgetJob.objects.filter(widget=widget):
                    wjob.delete()
                widget.delete()

            report = Report.objects.filter(id=rid)
            for criteria in report.criteria.all():
                if len(criteria.report_set.all()) == 1:
                    criteria.delete()

            report.delete()

        if options['clear_devices']:
            # clear references to existing devices
            DeviceManager.clear()
