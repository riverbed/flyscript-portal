# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import Column
from apps.devices.models import Device
from apps.report.models import Report
import apps.report.modules.yui3 as yui3
from apps.datasource.modules.profiler import GroupByTable, TimeSeriesTable
from apps.datasource.modules.shark import SharkTable, create_shark_column

#### Load devices that are defined
PROFILER = Device.objects.get(name="profiler")
SHARK1 = Device.objects.get(name="shark1")

#
# Profiler report
#

report = Report(title="Profiler", position=2)
report.save()

# Define a Overall TimeSeries showing Avg Bytes/s
table = TimeSeriesTable.create('ts-overall', PROFILER, duration=60)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "Overall Traffic", width=12)

# Define a TimeSeries showing Avg Bytes/s for tcp/80
table = TimeSeriesTable.create('ts-tcp80', PROFILER, duration=60,
                               filterexpr = 'tcp/80')

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units = 'B/s')
Column.create(table, 'avg_bytes_rtx', 'Avg Retrans Bytes/s', datatype='bytes', units = 'B/s')

yui3.TimeSeriesWidget.create(report, table, "Bandwidth for tcp/80",
                             altaxis=['avg_bytes_rtx'])

# Define a TimeSeries showing Avg Bytes/s for tcp/443
table = TimeSeriesTable.create('ts-tcp443', PROFILER, duration=60,
                               filterexpr = 'tcp/443')

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units = 'B/s')
Column.create(table, 'avg_bytes_rtx', 'Avg Retrans Bytes/s', datatype='bytes', units = 'B/s')

yui3.TimeSeriesWidget.create(report, table, "Bandwidth for tcp/443")

# Define a Pie Chart for locations
table = GroupByTable.create('location-bytes', PROFILER, 'host_group', duration=60)

Column.create(table, 'group_name', 'Group Name', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units = 'B/s', issortcol=True) 

yui3.PieWidget.create(report, table, "Locations by Bytes")

# Define a Table
table = GroupByTable.create('location-resptime', PROFILER, 'host_group', duration=60)

Column.create(table, 'group_name', 'Group Name', iskey=True)
Column.create(table, 'response_time', 'Response Time', units='s', issortcol=True)

yui3.BarWidget.create(report, table, "Locations by Response Time")
