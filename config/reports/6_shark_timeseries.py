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
from apps.report.models import Report, Table
from apps.datasource.modules.shark import SharkTable, create_shark_column
import apps.report.modules.yui3 as yui3

#### Customize devices and authorization here

tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Define a Shark Report and Table
#
report = Report(title="Shark Timeseries", position=5)
report.save()

### Table and Widget 1

t = SharkTable.create(name='Packet Traffic', devicename=v10, view='jobs/Flyscript-tests-job', duration=10, aggregated=False)


create_shark_column(t, 'time', extractor='generic.absolute_time', iskey=False, label='Time (ns)')
create_shark_column(t, 'generic_bytes', label='Bytes', iskey=False, extractor='generic.bytes', operation='sum')

yui3.TimeSeriesWidget.create(report, t, "Shark Packets (last 10 minutes)", width=12)

### Table and Widget 2

t = SharkTable.create(name='Detailed Packet Traffic', devicename=v10, view='jobs/Flyscript-tests-job', duration=10, aggregated=False)

create_shark_column(t, 'time', extractor='generic.absolute_time', iskey=False, label='Time (ns)')
create_shark_column(t, 'udp_bytes', extractor='udp.bytes', iskey=False, operation='sum', label='UDP Bytes')
yui3.TimeSeriesWidget.create(report, t, "Packets By Type", width=12)

### Table and Widget 3

t = SharkTable.create(name='Detailed Packet Traffic', devicename=v10, view='jobs/Flyscript-tests-job', duration=10, aggregated=False)
create_shark_column(t, 'time', extractor='generic.absolute_time', iskey=False, label='Time (ns)')
create_shark_column(t, 'tcp_bytes', extractor='tcp.bytes', iskey=False, operation='sum', label='TCP Bytes')
yui3.TimeSeriesWidget.create(report, t, "Packets By Type", width=12)

