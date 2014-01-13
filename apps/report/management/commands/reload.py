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
from django.core.exceptions import ObjectDoesNotExist

from apps.report.models import Report
from apps.devices.devicemanager import DeviceManager
from apps.plugins import plugins

from project import settings
from project.utils import Importer


class Command(BaseCommand):
    args = None
    help = 'Reloads the configuration defined in the config directory'

    option_list = BaseCommand.option_list + (
        optparse.make_option('--report-id',
                             action='store',
                             dest='report_id',
                             default=None,
                             help='Reload single report.'),

        optparse.make_option('--report-name',
                             action='store',
                             dest='report_name',
                             default=None,
                             help='Reload single report by fully qualified name.'),

        optparse.make_option('--report-dir',
                             action='store',
                             dest='report_dir',
                             default=None,
                             help='Reload reports from this directory.'),
    )

    def handle(self, *args, **options):
        self.stdout.write('Reloading report objects ... ')

        management.call_command('clean_pyc', path=settings.PROJECT_ROOT)
        management.call_command('syncdb', interactive=False)

        importer = Importer(buf=self.stdout)

        if options['report_id']:
            # single report
            pk = int(options['report_id'])
            report_name = Report.objects.get(pk=pk).sourcefile
            management.call_command('clean',
                                    applications=False,
                                    report_id=options['report_id'],
                                    clear_cache=True,
                                    clear_logs=False)
        elif options['report_name']:
            # single report
            report_name = options['report_name']
            try:
                report_id = Report.objects.get(sourcefile__endswith=report_name).id
                management.call_command('clean',
                                        applications=False,
                                        report_id=report_id,
                                        clear_cache=True,
                                        clear_logs=False)
            except ObjectDoesNotExist:
                pass

            DeviceManager.clear()
            modules = [report_name, 'config.reports.%s' % report_name]
            success = False
            for module in modules:
                try:
                    importer.import_file(report_name, module)
                    success = True
                except ImportError:
                    pass

            if not success:
                raise ImportError("No module found matching '%s'" % report_name)

            return

        else:
            # clear all data
            report_name = None
            management.call_command('clean',
                                    applications=True,
                                    report_id=None,
                                    clear_cache=True,
                                    clear_logs=False)

        # start with fresh device instances
        DeviceManager.clear()

        report_dir = os.path.join(settings.PROJECT_ROOT,
                                  options['report_dir'] or 'config')

        importer.import_directory(report_dir, report_name=report_name)

        for plugin in plugins.enabled():
            if plugin.reports:
                #from IPython import embed; embed()
                plugin.load_reports()
