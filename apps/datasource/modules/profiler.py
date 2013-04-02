# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import time
import pickle
import logging
import threading
import datetime

import rvbd.profiler
from rvbd.profiler.filters import TimeFilter, TrafficFilter

from apps.datasource.models import Column
from apps.datasource.devicemanager import DeviceManager
from project import settings
from libs.options import Options

logger = logging.getLogger(__name__)
lock = threading.Lock()
#import mock
#lock = mock.MagicMock()

def DeviceManager_new(*args, **kwargs):
    # Used by DeviceManger to create a Profiler instance
    return rvbd.profiler.Profiler(*args, **kwargs)


class TableOptions(Options):
    def __init__(self, groupby, realm=None, centricity=None, *args, **kwargs):
        super(TableOptions, self).__init__(*args, **kwargs)
        self.groupby = groupby
        self.realm = realm
        self.centricity = centricity

class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job
        
    def run(self):
        table = self.table
        options = table.get_options()

        profiler = DeviceManager.get_device(table.device.id)
        report = rvbd.profiler.report.SingleQueryReport(profiler)

        columns = [col.name for col in table.get_columns()]

        sortcol=None
        if table.sortcol is not None:
            sortcol=table.sortcol.name

        realm = options.realm or 'traffic_summary'

        criteria = self.job.get_criteria()
        tf = TimeFilter(start=datetime.datetime.fromtimestamp(criteria.t0),
                        end=datetime.datetime.fromtimestamp(criteria.t1))

        with lock:
            report.run(realm=realm,
                       groupby=profiler.groupbys[options.groupby],
                       columns=columns,
                       timefilter=tf, 
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

        return True

