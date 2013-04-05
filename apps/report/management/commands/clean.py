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

from project import settings
from apps.report.models import Report
from apps.datasource.devicemanager import DeviceManager


class Command(BaseCommand):
    args = None
    help = 'Clears existing data caches and logs'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--all',
                             action='store_true',
                             dest='all',
                             default=False,
                             help='Start from scratch, deleting database.'),
    )

    def handle(self, *args, **options):

        # clear cache files
        for f in os.listdir(settings.DATA_CACHE):
            if f != '.gitignore':
                os.unlink(os.path.join(settings.DATA_CACHE, f))

        # empty the existing logs
        for k, v in settings.LOGGING['handlers'].iteritems():
            try:
                open(v['filename'], 'w').close()
            except KeyError:
                pass

        # reset database
        if options['all']:
            #management.call_command('reset_db', router='default', interactive=False)
            apps = ['report', 'geolocation', 'datasource']
            for app in apps:
                for model in get_models(get_app(app)):
                    print 'Deleting objects from %s' % model
                    model.objects.all().delete()
            # clear references to existing devices
            DeviceManager.clear()



