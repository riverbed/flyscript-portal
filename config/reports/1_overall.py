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

from apps.datasource.models import Device, Column
from apps.report.models import Report
import apps.report.modules.yui3 as yui3
from apps.datasource.modules.profiler import TimeSeriesTable

#### Load devices that are defined
tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Overall report
#

report = Report(title="Overall", position=1)
report.save()

# Define a Overall TimeSeries showing Avg Bytes/s
table = TimeSeriesTable.create('ts1', 'tm08-1', duration=60)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')
Column.create(table, 'avg_bytes_rtx', 'Avg Retrans Bytes/s', datatype='bytes', units = 'B/s')

yui3.TimeSeriesWidget.create(report, table, "Overall Traffic", width=12)

