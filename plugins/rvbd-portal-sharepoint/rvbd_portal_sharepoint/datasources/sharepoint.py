# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging
from rvbd.common.jsondict import JsonDict


from rvbd_portal.apps.datasource.models import Table, Column
from rvbd_portal.apps.devices.devicemanager import DeviceManager
from rvbd_portal.apps.devices.forms import fields_add_device_selection


logger = logging.getLogger(__name__)


class TableOptions(JsonDict):
    _default = {'site_url': '',
                'list_name': ''}


class SharepointTable(object):
    @classmethod
    def create(cls, name, site_url, list_name, **kwargs):
        logger.debug('Creating Sharepoint table %s' % name)

        options = TableOptions(site_url=site_url, list_name=list_name)

        t = Table(name=name, module=__name__, options=options, **kwargs)
        t.save()

        fields_add_device_selection(t,
                                    keyword='sharepoint_device',
                                    label='Sharepoint',
                                    module='sharepoint_device',
                                    enabled=True)
        return t


def create_sharepoint_column(table, name, datatype='', issortcol=False):
    c = Column.create(table, name, label=name, datatype=datatype,
                      issortcol=issortcol)
    c.save()
    return c


class TableQuery(object):
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        """ Main execution method
        """

        criteria = self.job.criteria

        if criteria.sharepoint_device == '':
            logger.debug('%s: No sharepoint device selected' % self.table)
            self.job.mark_error("No Sharepoint Device Selected")
            return False

        sp = DeviceManager.get_device(criteria.sharepoint_device)

        site = sp.get_site_object(self.table.options.site_url)

        site_instance = site.lists[self.table.options.list_name]
        fields = [tc.name for tc in self.table.get_columns(synthetic=False)]

        self.data = []
        for row in site_instance.rows:
            d = [getattr(row, f) for f in fields]
            self.data.append(d)

        logger.info("SharepointTable job %s returning %s data" %
                    (self.job, len(self.data)))

        return True
