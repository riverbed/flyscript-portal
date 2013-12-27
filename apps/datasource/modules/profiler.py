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

import rvbd.profiler
from rvbd.profiler.filters import TimeFilter, TrafficFilter
from rvbd.common.jsondict import JsonDict

from apps.datasource.models import Table
from apps.devices.devicemanager import DeviceManager
from apps.datasource.forms import criteria_add_time_selection

logger = logging.getLogger(__name__)
lock = threading.Lock()

def new_device_instance(*args, **kwargs):
    # Used by DeviceManager to create a Profiler instance
    return rvbd.profiler.Profiler(*args, **kwargs)


class TableOptions(JsonDict):
    _default = {'groupby': None,
                'realm': None,
                'centricity': None}


class TimeSeriesTable:
    @classmethod
    def create(cls, name, device, duration,
               interface=False, **kwargs):
        """ Create a Profiler TimeSeriesTable.

        `duration` is in minutes

        """
        logger.debug('Creating Profiler TimeSeries table %s (%d)' % (name, duration))

        options = TableOptions(groupby='time',
                               realm='traffic_overall_time_series',
                               centricity='int' if interface else 'hos')

        t = Table(name=name, module=__name__, device=device, duration=duration*60,
                  options=options, **kwargs)
        t.save()

        criteria_add_time_selection(t, initial_duration="%d min" % duration)
        return t
        

class GroupByTable:
    @classmethod
    def create(cls, name, device, groupby, duration, 
               filterexpr=None, interface=False, **kwargs):
        """ Create a Profiler TimeSeriesTable.

        `duration` is in minutes

        """
        msg = 'Creating Profiler GroupBy table %s (%s, %d, %s)'
        logger.debug(msg % (name, groupby, duration, filterexpr))

        options = TableOptions(groupby=groupby,
                               realm='traffic_summary',
                               centricity='int' if interface else 'hos')

        t = Table(name=name, module=__name__, device=device, duration=duration*60,
                  filterexpr=filterexpr, options=options, **kwargs)
        t.save()
        criteria_add_time_selection(t, initial_duration="%d min" % duration)
        return t
        

class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def fake_run(self):
        import fake_data
        self.data = fake_data.make_data(self.table)
        
    def run(self):
        """ Main execution method
        """
        #self.fake_run()
        #return

        profiler = DeviceManager.get_device(self.table.device.id)
        report = rvbd.profiler.report.SingleQueryReport(profiler)

        columns = [col.name for col in self.table.get_columns(synthetic=False)]

        sortcol = None
        if self.table.sortcol is not None:
            sortcol = self.table.sortcol.name

        criteria = self.job.criteria
        tf = TimeFilter(start=criteria.starttime,
                        end=criteria.endtime)

        logger.info("Running Profiler table %d report for timeframe %s" % (self.table.id,
                                                                           str(tf)))

        # process Report/Table Criteria
        self.table.apply_table_criteria(criteria)

        if self.table.datafilter:
            datafilter = self.table.datafilter.split(',')
        else:
            datafilter = None

        with lock:
            report.run(realm=self.table.options.realm,
                       groupby=profiler.groupbys[self.table.options.groupby],
                       centricity=self.table.options.centricity,
                       columns=columns,
                       timefilter=tf, 
                       trafficexpr=TrafficFilter(self.job.combine_filterexprs()),
                       data_filter=datafilter,
                       resolution="%dmin" % (int(self.table.resolution / 60)),
                       sort_col=sortcol,
                       sync=False
                       )

        done = False
        logger.info("Waiting for report to complete")
        while not done:
            time.sleep(0.5)
            with lock:
                s = report.status()

            self.job.safe_update(progress = int(s['percent']))
            done = (s['status'] == 'completed')

        # Retrieve the data
        with lock:
            query = report.get_query_by_index(0)
            self.data = query.get_data()

            # Update criteria
            criteria.starttime = query.actual_t0
            criteria.endtime = query.actual_t1

        self.job.safe_update(actual_criteria = criteria)

        if self.table.rows > 0:
            self.data = self.data[:self.table.rows]

        logger.info("Report %s returned %s rows" % (self.job, len(self.data)))
        return True
