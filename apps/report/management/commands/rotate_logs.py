# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import logging

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    args = None
    help = 'Rotates log files.'

    def handle(self, *args, **options):
        db_logger = logging.getLogger('django.db.backends')
        db_logger.info('rolling db log')
        db_logger.handlers[0].doRollover()

        # there seems to be a hierarchy so we need to call
        # the module parent logger to get to the actual logHandler
        logger = logging.getLogger(__name__)
        logger.info('rolling default log')
        logger.parent.handlers[0].doRollover()
