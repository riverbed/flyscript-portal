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
from apps.datasource.modules.profiler import TimeSeriesTable, GroupByTable
from apps.datasource.modules.shark import ColumnOptions as shark_ColumnOptions
import apps.report.modules.yui3 as yui3

#### Load devices that are defined
tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Profiler report
#

report = Report(title="Interface QoS", position=1)
report.save()

# Define a Overall TimeSeries 
table = TimeSeriesTable.create('if-qos-overall', 'tm08-1', duration=60,
                               interface=True)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_util', 'Avg % Util (in)')
Column.create(table, 'out_avg_util', 'Avg % Util (out)')

yui3.TimeSeriesWidget.create(report, table, "Avg % Utilization", width=12)


# Define a Overall TimeSeries 
table = TimeSeriesTable.create('ts-overall', 'tm08-1', duration=60,
                               filterexpr="qos EF",
                               interface=True)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_bytes', 'Avg Bytes/s (in)')
Column.create(table, 'out_avg_bytes', 'Avg Bytes/s (out)')

yui3.TimeSeriesWidget.create(report, table, "QoS EF - Avg Bytes/s", width=12)

# Define a Overall TimeSeries 
table = TimeSeriesTable.create('ts-overall', 'tm08-1', duration=60,
                               filterexpr="qos AF11",
                               interface=True)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_bytes', 'Avg Bytes/s (in)')
Column.create(table, 'out_avg_bytes', 'Avg Bytes/s (out)')

yui3.TimeSeriesWidget.create(report, table, "QoS AF11 - Avg Bytes/s", width=12)

# Define a Overall TimeSeries 
table = TimeSeriesTable.create('ts-overall', 'tm08-1', duration=60,
                               filterexpr="qos Default",
                               interface=True)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_bytes', 'Avg Bytes/s (in)')
Column.create(table, 'out_avg_bytes', 'Avg Bytes/s (out)')

yui3.TimeSeriesWidget.create(report, table, "QoS Default - Avg Bytes/s", width=12)

# Define a Overall TimeSeries 
table = GroupByTable.create('ts-overall', 'tm08-1', 'qos', duration=60,
                            interface=True)

Column.create(table, 'qos_name', 'QoS')
Column.create(table, 'in_avg_bytes', 'Avg Bytes/s (in)')
Column.create(table, 'out_avg_bytes', 'Avg Bytes/s (out)')

yui3.TableWidget.create(report, table, "QoS Table", width=12)

