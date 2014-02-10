# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import time
import logging
import threading
import datetime
import pandas

import rvbd.profiler
from rvbd.profiler.filters import TimeFilter, TrafficFilter
from rvbd.common.jsondict import JsonDict
from rvbd.common.timeutils import (parse_timedelta, timedelta_total_seconds)

from rvbd_portal.apps.datasource.models import Table, TableField
from rvbd_portal.apps.devices.forms import fields_add_device_selection
from rvbd_portal.apps.devices.devicemanager import DeviceManager
from rvbd_portal.apps.datasource.forms import (fields_add_time_selection,
                                               fields_add_resolution)
from rvbd_portal.libs.fields import Function

from rvbd_portal_profiler.datasources.profiler import (fields_add_filterexpr,
                                                       fields_add_filterexprs_field)

logger = logging.getLogger(__name__)
lock = threading.Lock()


class TableOptions(JsonDict):
    _default = {'template_id': None}
    _required = ('template_id',)


class ProfilerTemplateTable(object):
    @classmethod
    def create(cls, name, template_id, duration,
               resolution='auto', filterexpr=None, **kwargs):
        """ Create a ProfilerTemplateTable.

        This queries a Profiler saved report template rather than creating
        a new report from scratch.

        `template_id` is a saved-report template ID
        `duration` is in minutes or a string like '15min'
        """
        logger.debug('Creating ProfilerTemplateTable table %s (%s) - %s/%s' %
                     (name, template_id, duration, resolution))

        options = TableOptions(template_id=template_id)

        t = Table(name=name, module=__name__, 
                  filterexpr=filterexpr, options=options, **kwargs)
        t.save()

        if resolution != 'auto':
            if isinstance(resolution, int):
                res = resolution
            else:
                res = int(timedelta_total_seconds(parse_timedelta(resolution)))
            resolution = rvbd.profiler.report.Report.RESOLUTION_MAP[res]

        if isinstance(duration, int):
            duration = "%d min" % duration

        fields_add_device_selection(t, keyword='profiler_device',
                                    label='Profiler', module='profiler',
                                    enabled=True)
        fields_add_time_selection(t, initial_duration=duration)
        
        fields_add_filterexpr(t)
        fields_add_resolution(t, initial=resolution,
                              resolutions=[('auto', 'Automatic'),
                                           '1min', '15min', 'hour', '6hour'],
                              special_values=['auto'])
        return t


class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        """ Main execution method. """
        criteria = self.job.criteria

        if criteria.profiler_device == '':
            logger.debug('%s: No profiler device selected' % self.table)
            self.job.mark_error("No Profiler Device Selected")
            return False
            
        profiler = DeviceManager.get_device(criteria.profiler_device)
        report = rvbd.profiler.report.MultiQueryReport(profiler)

        tf = TimeFilter(start=criteria.starttime,
                        end=criteria.endtime)

        logger.info("Running ProfilerTemplateTable table %d report "
                    "for timeframe %s" % (self.table.id, str(tf)))

        trafficexpr = TrafficFilter(
            self.job.combine_filterexprs(exprs=criteria.profiler_filterexpr)
        )

        # Incoming criteria.resolution is a timedelta
        logger.debug('Profiler report got criteria resolution %s (%s)' %
                     (criteria.resolution, type(criteria.resolution)))
        if criteria.resolution != 'auto':
            rsecs = int(timedelta_total_seconds(criteria.resolution))
            resolution = rvbd.profiler.report.Report.RESOLUTION_MAP[rsecs]
        else:
            resolution = 'auto'
        
        logger.debug('Profiler report using resolution %s (%s)' %
                     (resolution, type(resolution)))

        with lock:
            res = report.run(template_id=self.table.options.template_id,
                             timefilter=tf,
                             trafficexpr=trafficexpr,
                             resolution=resolution)

        if res is True:
            logger.info("Report template complete.")
            self.job.safe_update(progress=100)

        # Retrieve the data
        with lock:
            query = report.get_query_by_index(0)
            data = query.get_data()
            headers = report.get_legend()

            tz = criteria.starttime.tzinfo
            # Update criteria
            criteria.starttime = (datetime.datetime
                                  .utcfromtimestamp(query.actual_t0)
                                  .replace(tzinfo=tz))
            criteria.endtime = (datetime.datetime
                                .utcfromtimestamp(query.actual_t1)
                                .replace(tzinfo=tz))

        self.job.safe_update(actual_criteria=criteria)

        # create dataframe with all of the default headers
        df = pandas.DataFrame(data, columns=[h.key for h in headers])

        # now filter down to the columns requested by the table
        columns = [col.name for col in self.table.get_columns(synthetic=False)]
        self.data = df[columns]

        if self.table.sortcol is not None:
            self.data = self.data.sort(self.table.sortcol.name)

        if self.table.rows > 0:
            self.data = self.data[:self.table.rows]

        logger.info("Report %s returned %s rows" % (self.job, len(self.data)))
        return True
