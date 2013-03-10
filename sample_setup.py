# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


# -*- coding: utf-8 -*-
from random import randint
import sys, os
import pickle
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from report.models import *

profiler = Device(name="tm08-1",
                  sourcetype="profiler",
                  host="tm08-1.lab.nbttech.com",
                  port=443,
                  username="admin",
                  password="admin")
profiler.save()
   
main = Report(title="Main")
main.save()



# Define a TimeSeries 
dt = DataTable(source='profiler', duration=60, options={'device': profiler.id,
                                                        'realm': 'traffic_overall_time_series',
                                                        'groupby': 'time'})
dt.save()
c = DataColumn(datatable=dt, querycol = 'time', label = 'Time', datatype='time')
c.save()
c = DataColumn(datatable=dt, querycol = 'avg_bytes', label = 'Avg Bytes/s', datatype='bytes')
c.save()
c = DataColumn(datatable=dt, querycol = 'network_rtt', label = 'RTT', datatype='metric')
c.save()

wid = Widget(report=main, title="Overall Bandwidth", datatable = dt,
             row=1, col=1, rows=10, colwidth=12,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']},
                               '1': {'title': 'ms',
                                     'position': 'right',
                                     'columns': ['network_rtt']},
             }},
             uilib="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})

wid.save()

# Define a DataTable
dt = DataTable(source='profiler', duration=60,
               options={'device': profiler.id,
                        'groupby': 'port'})
dt.save()
port = DataColumn(datatable=dt, querycol = 'port', label = 'Port', datatype='port')
port.save()
avgbytes = DataColumn(datatable=dt, querycol = 'avg_bytes', label = 'Avg Bytes/s', datatype='bytes')
avgbytes.save()
dt.sortcol = avgbytes
dt.save()
avgpkts = DataColumn(datatable=dt, querycol = 'avg_pkts', label = 'Avg Packets/s')
avgpkts.save()

wid = Widget(report=main, title="Ports", datatable = dt, 
             row=2, col=1, rows=1000, colwidth=6,
             uilib="yui3", uiwidget="TableWidget", uioptions = {'minHeight': 300})
wid.save()

wid = Widget(report=main, title="Ports", datatable = dt, 
             row=2, col=2, rows=10, colwidth=6, 
             options = {'key': 'port',
                        'value': 'avg_bytes'},
             uilib="yui3", uiwidget="PieWidget",
             uioptions = {'minHeight': 300})

wid.save()

wid = Widget(report=main, title="Ports", datatable = dt, 
             row=3, col=1, rows=10, colwidth=6, 
             options = {'key': 'port',
                        'values': ['avg_bytes']},
             uilib="yui3", uiwidget="BarWidget",
             uioptions = {'minHeight': 300})

wid.save()


# Define a TimeSeries for RTT+ServerDelay
dt = DataTable(source='profiler', duration=60, options={'device': profiler.id,
                                                        'realm': 'traffic_overall_time_series',
                                                        'groupby': 'time'})
dt.save()
c = DataColumn(datatable=dt, querycol = 'time', label = 'Time', datatype='time')
c.save()
c = DataColumn(datatable=dt, querycol = 'network_rtt', label = 'RTT', datatype='metric')
c.save()
c = DataColumn(datatable=dt, querycol = 'server_delay', label = 'Serv Delay', datatype='metric' )
c.save()

wid = Widget(report=main, title="RTT + Server Delay", datatable = dt, 
             row=3, col=2, rows=10, colwidth=6,
             options = { 'stacked' : True},
             uilib="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})

wid.save()

