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

from rvbd_portal.apps.report.models import Report
from rvbd_portal.apps.devices.devicemanager import DeviceManager

from django.conf import settings
from project.utils import Importer
from rvbd_portal.apps.plugins import plugins


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

        optparse.make_option('--namespace',
                             action='store',
                             dest='namespace',
                             default=None,
                             help='Reload reports under this namespace.'),
    )

    def import_module(self, module):

        #module = report.sourcefile
        report_name = module.split('.')[-1]
        try:
            self.importer.import_file(report_name, module)
        except ImportError as e:
            msg = "Failed to import module '%s': %s" % (report_name,
                                                        str(e))
            raise ImportError(msg)

    def handle(self, *args, **options):
        self.stdout.write('Reloading report objects ... ')

        management.call_command('clean_pyc', path=settings.PROJECT_ROOT)
        management.call_command('syncdb', interactive=False)

        self.importer = Importer(buf=self.stdout)

        if options['report_id']:
            # single report
            report_id = options['report_id']
            pk = int(report_id)
            report = Report.objects.get(pk=pk)

            management.call_command('clean',
                                    applications=False,
                                    report_id=report_id,
                                    clear_cache=False,
                                    clear_logs=False)

            DeviceManager.clear()
            self.import_module(report.sourcefile)

        elif options['report_name']:
            name = options['report_name']
            try:
                report = Report.objects.get(sourcefile__endswith=name)
                report_id = report.id

                management.call_command('clean',
                                        applications=False,
                                        report_id=report_id,
                                        clear_cache=False,
                                        clear_logs=False)
                self.import_module(report.sourcefile)
            except ObjectDoesNotExist:
                self.import_module(name)

            DeviceManager.clear()

        elif options['namespace']:
            reports = Report.objects.filter(namespace=options['namespace'])

            for report in reports:
                management.call_command('clean',
                                        applications=False,
                                        report_id=report.id,
                                        clear_cache=False,
                                        clear_logs=False)
                self.import_module(report.sourcefile)

        else:
            # clear all data
            management.call_command('clean',
                                    applications=True,
                                    report_id=None,
                                    clear_cache=True,
                                    clear_logs=False)

            # start with fresh device instances
            DeviceManager.clear()

            report_dir = os.path.join(settings.PROJECT_ROOT,
                                      options['report_dir'] or 'config')

            self.importer.import_directory(report_dir, report_name=None)

            for plugin in plugins.enabled():
                if plugin.reports:
                    #from IPython import embed; embed()
                    plugin.load_reports()
