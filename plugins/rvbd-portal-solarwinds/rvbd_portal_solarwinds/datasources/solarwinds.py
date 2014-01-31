# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging
import pandas

import rvbd.profiler
from rvbd.profiler.filters import TrafficFilter

from rvbd_portal.apps.datasource.models import Table
from rvbd_portal.apps.devices.devicemanager import DeviceManager
from rvbd_portal.apps.devices.forms import fields_add_device_selection


logger = logging.getLogger(__name__)


class SolarwindsTable(object):
    @classmethod
    def create(cls, name, **kwargs):
        logger.debug('Creating Solarwinds table %s' % name)

        t = Table(name=name, module=__name__, **kwargs)
        t.save()

        fields_add_device_selection(t,
                                    keyword='solarwinds_device',
                                    label='Solarwinds',
                                    module='solarwinds',
                                    enabled=True)
        return t


class TableQuery(object):
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        """ Main execution method
        """

        criteria = self.job.criteria

        if criteria.solarwinds_device == '':
            logger.debug('%s: No solarwinds device selected' % self.table)
            self.job.mark_error("No Solarwinds Device Selected")
            return False

        sw = DeviceManager.get_device(criteria.profiler_device)

        # TODO add queries
        self.data = None

        logger.info("SolarwindsTable job %s returning %s data" %
                    (self.job, len(self.data)))
        return True



