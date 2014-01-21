# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.yui3 as yui3
import rvbd_portal.apps.report.modules.maps as maps

from rvbd_portal_profiler.datasources.profiler import GroupByTable, TimeSeriesTable
from rvbd_portal.apps.datasource.modules.shark import SharkTable, create_shark_column

#
# Overall report
#

report = Report(title="Overall", position=1,
                field_order = ['endtime', 'profiler_filterexpr', 'shark_filterexpr'],
                hidden_fields = ['resolution', 'duration'])
report.save()

section = Section.create(report, title = 'Locations',
                         section_keywords = ['resolution', 'duration'])
                         
# Define a map and table, group by location
table = GroupByTable.create('maploc', 'host_group', duration=60, resolution='auto')

Column.create(table, 'group_name',    label='Group Name', iskey=True)
Column.create(table, 'response_time', label='Resp Time',  datatype='metric')
Column.create(table, 'network_rtt',   label='Net RTT',    datatype='metric')
Column.create(table, 'server_delay',  label='Srv Delay',  datatype='metric')

maps.MapWidget.create(section, table, "Response Time", width=6, height=300)
yui3.TableWidget.create(section, table, "Locations by Avg Bytes", width=6)

# Define a Overall TimeSeries showing Avg Bytes/s
section = Section.create(report, title = 'Profiler Overall',
                         section_keywords = ['resolution', 'duration'])

table = TimeSeriesTable.create('ts1', duration=1440, resolution='15min')

Column.create(table, 'time',      label='Time',        datatype='time',  iskey=True)
Column.create(table, 'avg_bytes', label='Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(section, table, "Profiler Overall Traffic", width=6)

### Shark Time Series
section = Section.create(report, title = 'Shark Traffic',
                         section_keywords = ['resolution', 'duration', ])

t = SharkTable.create(name='Total Traffic Bytes',
                      duration=15, resolution='1sec', aggregated=False)

create_shark_column(t, 'time', extractor='sample_time', iskey=True, label='Time', datatype='time')
create_shark_column(t, 'generic_bytes', label='Avg Bytes/s', iskey=False,
                    extractor='generic.bytes', operation='sum', datatype='bytes')

yui3.TimeSeriesWidget.create(section, t, 'Overall Bandwidth (Bytes) at (1-second resolution)',
                             width=6)
