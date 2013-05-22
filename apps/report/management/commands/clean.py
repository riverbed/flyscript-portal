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

from django.core.management.base import BaseCommand, CommandError
from django.core import management
from django.db.models import get_app, get_models
from apps.datasource.models import Column, Job, Device

from project import settings
from apps.report.models import Report, Widget, WidgetJob
from apps.datasource.devicemanager import DeviceManager


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

        # empty the existing logs
        for k, v in settings.LOGGING['handlers'].iteritems():
            try:
                open(v['filename'], 'w').close()
            except KeyError:
                pass

        # reset database
        if options['applications']:
            apps = ['report', 'geolocation', 'datasource', 'console']
            for app in apps:
                for model in get_models(get_app(app)):
                    if model != Device:
                        print 'Deleting objects from %s' % model
                        model.objects.all().delete()
        elif options['report_id']:
            # remove Report and its Widgets, Jobs, WidgetJobs, Tables and Columns
            rid = options['report_id']

            for widget in Widget.objects.filter(report=rid):
                for table in widget.tables.all():
                    for column in Column.objects.filter(table=table.id):
                        column.delete()
                    for job in Job.objects.filter(table=table.id):
                        job.delete()
                    table.delete()
                for wjob in WidgetJob.objects.filter(widget=widget):
                    wjob.delete()
                widget.delete()
            Report.objects.filter(id=rid).delete()

        if options['clear_devices']:
            # clear references to existing devices
            DeviceManager.clear()



