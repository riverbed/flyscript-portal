# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import os
import logging
import optparse

from django.core.management.base import BaseCommand

from rvbd.common.utils import Formatter

from rvbd_portal.apps.datasource.models import Job

# not pretty, but pandas insists on warning about
# some deprecated behavior we really don't care about
# for this script, so ignore them all
import warnings
warnings.filterwarnings("ignore")


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    args = None
    help = 'Work with already run jobs'

    def create_parser(self, prog_name, subcommand):
        """ Override super version to include special option grouping
        """
        parser = super(Command, self).create_parser(prog_name, subcommand)
        group = optparse.OptionGroup(parser, "Job Help",
                                     "Helper commands to manange jobs")
        group.add_option('--job-list',
                         action='store_true',
                         dest='job_list',
                         default=False,
                         help='List all jobs')
        group.add_option('--job-age',
                         action='store_true',
                         dest='job_age',
                         default=False,
                         help='Delete old/ancient jobs')
        group.add_option('--job-flush',
                         action='store_true',
                         dest='job_flush',
                         default=False,
                         help='Delete all jobs without question')
        group.add_option('--job-data',
                         action='store',
                         dest='job_data',
                         default=False,
                         help='Print data associated with a job')
        parser.add_option_group(group)

        return parser

    def console(self, msg, ending=None):
        """ Print text to console except if we are writing CSV file """
        self.stdout.write(msg, ending=ending)
        self.stdout.flush()

    def handle(self, *args, **options):
        """ Main command handler. """

        if options['job_list']:
            # print out the id's instead of processing anything
            columns = ['ID', 'Table', 'Created', 'Touched', 'Sts', 'Refs',
                       'Progress', 'Data file']
            data = []
            for j in Job.objects.all():
                datafile = j.datafile()
                if not os.path.exists(datafile):
                    datafile += " (missing)"
                data.append([j.id, j.table.name, j.created, j.touched,
                             j.status, j.refcount, j.progress, datafile])

            Formatter.print_table(data, columns)

        elif options['job_data']:
            job = Job.objects.get(id=options['job_data'])

            columns = [c.name for c in job.table.get_columns()]

            if job.status == job.COMPLETE:
                Formatter.print_table(job.values(), columns)

        elif options['job_age']:
            logger.debug('Aging all jobs.')
            Job.age_jobs(force=True)

        elif options['job_flush']:
            logger.debug('Flushing all jobs.')
            while Job.objects.count():
                ids = Job.objects.values_list('pk', flat=True)[:100]
                Job.objects.filter(pk__in=ids).delete()
