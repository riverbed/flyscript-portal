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

#### Load devices that are defined
tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Overall report
#

report = Report(title="Overall", position=1)
report.save()

# Define a Overall TimeSeries showing Avg Bytes/s
dt = Table(name='ts1', module='profiler', device=tm08, duration=60, 
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
dt.save()
Column(table=dt, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

wid = Widget(report=report, title="Overall Traffic", 
             row=1, col=1, colwidth=12,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']}
                               }},
             module="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a TimeSeries showing Avg Bytes/s for tcp/80
dt = Table(name='ts2', module='profiler', device=tm08, duration=60,
           filterexpr = 'tcp/80',
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
dt.save()
Column(table=dt, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()
Column(table=dt, name='avg_bytes_rtx', iskey=False, label='Avg Retrans Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

wid = Widget(report=report, title="tcp/80", 
             row=2, col=1, colwidth=6,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes', 'avg_bytes_rtx']}
                               }},
             module="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a TimeSeries showing Avg Bytes/s for tcp/443
dt = Table(name='ts2', module='profiler', device=tm08, duration=60,
           filterexpr = 'tcp/443',
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
dt.save()
Column(table=dt, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()
Column(table=dt, name='avg_bytes_rtx', iskey=False, label='Avg Retrans Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

wid = Widget(report=report, title="tcp/443", 
             row=2, col=2, colwidth=6,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes', 'avg_bytes_rtx']}
                               }},
             module="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a Pie Chart for locations
dt = Table(name='hg', module='profiler', device=tm08, duration=60,
               options={'groupby': 'host_group'})
dt.save()
Column(table=dt, name='group_name', iskey=True, label = 'Group Name', position=1).save()
c = Column(table=dt, name='total_bytes', iskey=False, label = 'Total Bytes', datatype='bytes', units='B', position=2)
c.save()
dt.sortcol = c
dt.save()

wid = Widget(report=report, title="Locations by Bytes",  
             row=3, col=1, rows=10, colwidth=6, 
             options = {'key': 'group_name',
                        'value': 'total_bytes'},
             module="yui3", uiwidget="PieWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a Table
dt = Table(name='hg2', module='profiler', device=tm08, duration=60,
           options={'groupby': 'host_group'})
dt.save()
Column(table=dt, name='group_name', iskey=True, label = 'Group Name', position=1).save()
Column(table=dt, name='response_time', iskey=False, label = 'Response Time', datatype='metric', units='s', position=2).save()

wid = Widget(report=report, title="Locations by Response Time", 
             row=3, col=2, rows=10, colwidth=6, 
             options = {'key': 'group_name',
                        'values': ['response_time']},
             module="yui3", uiwidget="BarWidget",
             uioptions = {'minHeight': 300})

wid.save()
wid.tables.add(dt)

