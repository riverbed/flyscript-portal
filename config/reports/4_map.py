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
from apps.datasource.modules.profiler import TimeSeriesTable, GroupByTable
from apps.report.models import Report, Table
import apps.report.modules.google_maps as google_maps

#### Customize devices and authorization here

tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Google Map example
#

# Google Map example
report = Report(title="Map", position=4)
report.save()

# Define a table, group by location
table = GroupByTable.create('maploc',  tm08, 'host_group', duration=60, filterexpr='host 10.99/16')

Column.create(table, 'group_name', iskey=True, label='Group Name')
Column.create(table, 'avg_bytes', label='Avg Bytes/s', datatype='bytes')

# Map widget on top of that table
google_maps.MapWidget.create(report, table, "Avg Bytes/s", width=12, height=600)
