# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import os
import pickle
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import *
from apps.report.models import *
from apps.geolocation.models import *
from apps.datasource.modules.shark import ColumnOptions as shark_ColumnOptions
import apps.report.modules.yui3 as yui3

#### Load devices that are defined
tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Profiler report
#

report = Report(title="Profiler", position=1)
report.save()

# Define a Overall TimeSeries showing Avg Bytes/s
table = Table(name='ts1', module='profiler', device=tm08, duration=60, 
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
table.save()
Column(table=table, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=table, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

yui3.TimeSeriesWidget.create(report, table, "Overall Traffic", width=12)

# Define a TimeSeries showing Avg Bytes/s for tcp/80
table = Table(name='ts2', module='profiler', device=tm08, duration=60,
           filterexpr = 'tcp/80',
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
table.save()
Column(table=table, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=table, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()
Column(table=table, name='avg_bytes_rtx', iskey=False, label='Avg Retrans Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

yui3.TimeSeriesWidget.create(report, table, "tcp/80")

# Define a TimeSeries showing Avg Bytes/s for tcp/443
table = Table(name='ts2', module='profiler', device=tm08, duration=60,
           filterexpr = 'tcp/443',
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
table.save()
Column(table=table, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=table, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()
Column(table=table, name='avg_bytes_rtx', iskey=False, label='Avg Retrans Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

yui3.TimeSeriesWidget.create(report, table, "tcp/443")

# Define a Pie Chart for locations
table = Table(name='hg', module='profiler', device=tm08, duration=60,
               options={'groupby': 'host_group'})
table.save()
Column(table=table, name='group_name', iskey=True, label = 'Group Name', position=1).save()
c = Column(table=table, name='total_bytes', iskey=False, label = 'Total Bytes', datatype='bytes', units='B', position=2)
c.save()
table.sortcol = c
table.save()

yui3.PieWidget.create(report, table, "Locations by Bytes")

# Define a Table
table = Table(name='hg2', module='profiler', device=tm08, duration=60,
           options={'groupby': 'host_group'})
table.save()
Column(table=table, name='group_name', iskey=True, label = 'Group Name', position=1).save()
Column(table=table, name='response_time', iskey=False, label = 'Response Time', datatype='metric', units='s', position=2).save()

yui3.BarWidget.create(report, table, "Locations by Response Time")
