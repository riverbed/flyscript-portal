# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.yui3 as yui3

from rvbd_portal_profiler.datasources.profiler import (GroupByTable,
                                                       TimeSeriesTable)

#
# Profiler report
#

report = Report(title="Profiler", position=2)
report.save()

section = Section.create(report)

# Define a Overall TimeSeries showing Avg Bytes/s
table = TimeSeriesTable.create('ts-overall', duration=60, resolution="1min")

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(section, table, "Overall Traffic", width=12)

# Define a TimeSeries showing Avg Bytes/s for tcp/80
table = TimeSeriesTable.create('ts-tcp80', duration=60,
                               filterexpr = 'tcp/80', cacheable=False)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units = 'B/s')
Column.create(table, 'avg_bytes_rtx', 'Avg Retrans Bytes/s', datatype='bytes', units = 'B/s')

yui3.TimeSeriesWidget.create(section, table, "Bandwidth for tcp/80",
                             altaxis=['avg_bytes_rtx'])

# Define a TimeSeries showing Avg Bytes/s for tcp/443
table = TimeSeriesTable.create('ts-tcp443', duration=60,
                               filterexpr = 'tcp/443')

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units = 'B/s')
Column.create(table, 'avg_bytes_rtx', 'Avg Retrans Bytes/s', datatype='bytes', units = 'B/s')

yui3.TimeSeriesWidget.create(section, table, "Bandwidth for tcp/443")

# Define a Pie Chart for locations
table = GroupByTable.create('location-bytes', 'host_group', duration=60)

Column.create(table, 'group_name', 'Group Name', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units = 'B/s', issortcol=True) 

yui3.PieWidget.create(section, table, "Locations by Bytes")

# Define a Table
table = GroupByTable.create('location-resptime', 'host_group', duration=60)

Column.create(table, 'group_name', 'Group Name', iskey=True)
Column.create(table, 'response_time', 'Response Time', units='s', issortcol=True)

yui3.BarWidget.create(section, table, "Locations by Response Time")
