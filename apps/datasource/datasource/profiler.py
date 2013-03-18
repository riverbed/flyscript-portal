# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import time
import pickle
import logging
import threading

import rvbd.profiler
from rvbd.profiler.filters import TimeFilter, TrafficFilter

from apps.datasource.models import TableColumn
from apps.datasource.devicemanager import DeviceManager


logger = logging.getLogger('datasource')
lock = threading.Lock()

# Used by DeviceManger to create a Profiler instance
def DeviceManager_new(*args, **kwargs):
    return rvbd.profiler.Profiler(*args, **kwargs)

# Used by Table to actually run a query
class Table_Query:
    def __init__(self, table, job):
        self.table = table
        self.job = job
        
    def run(self):
        cachefile = "table-%s.cache" % self.table.id
        if os.path.exists(cachefile):
            # XXXCJ This cachefile hack is temporary and is only good for testing to avoid actually
            # having to run the report every single time.
            logger.debug("Using cache file")
            f = open(cachefile, "r")
            self.data = pickle.load(f)
            f.close()
        else:
            logger.debug("Running new report")
            table = self.table

            profiler = DeviceManager.get_device(table.options['device'])
            report = rvbd.profiler.report.SingleQueryReport(profiler)

            columns = []

            for tc in TableColumn.objects.filter(table=table).select_related():
                columns.append(tc.column.source_name)
                
            sortcol=None
            if table.sortcol is not None:
                sortcol=table.sortcol.source_name

            if 'realm' in table.options:
                realm = table.options['realm']
            else:
                realm = 'traffic_summary'

            with lock:
                report.run(realm=realm,
                           groupby=profiler.groupbys[table.options['groupby']],
                           columns=columns,
                           timefilter=TimeFilter.parse_range("last %d m" % table.duration),
                           trafficexpr = TrafficFilter(table.filterexpr),
                           resolution="%dmin" % (int(table.resolution / 60)),
                           sort_col=sortcol,
                           sync=False
                           )

            done = False
            logger.info("Waiting for report to complete")
            while not done:
                time.sleep(0.5)
                with lock:
                    s = report.status()

                self.job.progress = int(s['percent'])
                self.job.save()
                done = (s['status'] == 'completed')

            # Retrieve the data
            with lock:
                self.data = report.get_data()

            if table.rows > 0:
                self.data = self.data[:table.rows]
                
            f = open(cachefile, "w")
            pickle.dump(self.data, f)
            f.close()

        return True
