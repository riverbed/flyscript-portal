# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import Device, Column
from apps.report.models import Report
import apps.report.modules.yui3 as yui3
from apps.datasource.modules.profiler import GroupByTable, TimeSeriesTable
from apps.datasource.modules.shark import SharkTable, create_shark_column
import apps.report.modules.google_maps as google_maps

#### Load devices that are defined
PROFILER = Device.objects.get(name="profiler")
SHARK1 = Device.objects.get(name="shark1")

### Configure Shark View To Use
SHARK_VIEW_NAME = 'jobs/flyscript-portal'       # Note: must prefix job names with 'jobs/'
SHARK_VIEW_SIZE = '10%'                         # Default size to use if job does not already exist

#
# Overall report
#

report = Report(title="Overall", position=1)
report.save()

# Define a map and table, group by location
table = GroupByTable.create('maploc',  PROFILER, 'host_group', duration=60, filterexpr='host 10.99/16')

Column.create(table, 'group_name', iskey=True, label='Group Name')
Column.create(table, 'response_time', label='Resp Time', datatype='metric')
Column.create(table, 'network_rtt', label='Net RTT', datatype='metric')
Column.create(table, 'server_delay', label='Srv Delay', datatype='metric')

google_maps.MapWidget.create(report, table, "Response Time", width=6, height=300)
yui3.TableWidget.create(report, table, "Locations by Avg Bytes", width=6)

# Define a Overall TimeSeries showing Avg Bytes/s
table = TimeSeriesTable.create('ts1', PROFILER, duration=1440, resolution=(60*15))

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "Profiler Overall Traffic", width=6)

### Shark Time Series
t = SharkTable.create(name='Total Traffic Bytes', device=SHARK1, 
                      view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                      duration=10, resolution=1, aggregated=False)

create_shark_column(t, 'time', extractor='sample_time', iskey=True, label='Time', datatype='time')
create_shark_column(t, 'generic_bytes', label='Avg Bytes/s', iskey=False, 
                        extractor='generic.bytes', operation='sum', datatype='bytes')

yui3.TimeSeriesWidget.create(report, t, 'Overall Bandwidth (Bytes) at (1-second resolution)', width=6)
