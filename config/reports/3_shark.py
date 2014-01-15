# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ('License').  
# This software is distributed 'AS IS' as set forth in the License.

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

from rvbd_common.apps.report.models import Report, Section
import rvbd_common.apps.report.modules.yui3 as yui3
from apps.datasource.modules.shark import SharkTable, create_shark_column

### Configure Shark View To Use
SHARK_VIEW_NAME = 'jobs/flyscript-portal'       # Note: must prefix job names with 'jobs/'
SHARK_VIEW_SIZE = '10%'                         # Default size to use if job does not already exist

#
# Define a Shark Report and Table
#
report = Report(title='Shark', position=3)
report.save()

section = Section.create(report, section_keywords="device")

### Shark Time Series

t = SharkTable.create(name='Total Traffic Bytes', view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                      duration=1, resolution='1sec', aggregated=False)

create_shark_column(t, 'time', extractor='sample_time', iskey=True, label='Time', datatype='time')
create_shark_column(t, 'generic_bytes', label='Bytes', iskey=False, extractor='generic.bytes', operation='sum')

yui3.TimeSeriesWidget.create(section, t, 'Overall Bandwidth (Bytes)', width=12)

### Table for Shark
table = SharkTable.create(name='Packet Traffic', view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                            duration=1, aggregated=False)

create_shark_column(table, 'ip_src', label='Source IP', iskey=True, extractor='ip.src')
create_shark_column(table, 'ip_dst', label='Dest IP', iskey=True, extractor='ip.dst')
create_shark_column(table, 'generic_bytes', label='Bytes', iskey=False, extractor='generic.bytes', operation='sum',
                        datatype='bytes', issortcol=True)
create_shark_column(table, 'generic_packets', label='Packets', iskey=False, extractor='generic.packets', operation='sum',
                        datatype='metric')

yui3.TableWidget.create(section, table, 'Packets', width=12)

section = Section.create(report, section_keywords="device")

### Microbursts Graph for Shark 
table = SharkTable.create(name='MicroburstsTime', view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                            duration=1, aggregated=False)

create_shark_column(table, 'time', extractor='sample_time', iskey=True, label='Time (ns)', datatype='time')

create_shark_column(table, 'max_microburst_1ms_bytes', label='uBurst 1ms',
                    extractor='generic.max_microburst_1ms.bytes', operation='max', datatype='bytes')

create_shark_column(table, 'max_microburst_10ms_bytes', label='uBurst 10ms',
                    extractor='generic.max_microburst_10ms.bytes', operation='max',  datatype='bytes')

create_shark_column(table, 'max_microburst_100ms_bytes', label='uburst 100ms',
                    extractor='generic.max_microburst_100ms.bytes', operation='max',  datatype='bytes')

yui3.TimeSeriesWidget.create(section, table, 'Microbursts Summary Bytes', width=6)

### Microbursts Table for Shark
table = SharkTable.create(name='MicroburstsTable', view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                            duration=1, aggregated=False)

create_shark_column(table, 'max_microburst_1ms_bytes', label='uBurst 1ms',
                    extractor='generic.max_microburst_1ms.bytes', operation='max', datatype='bytes')

create_shark_column(table, 'max_microburst_10ms_bytes', label='uBurst 10ms',
                    extractor='generic.max_microburst_10ms.bytes', operation='max',  datatype='bytes')

create_shark_column(table, 'max_microburst_100ms_bytes', label='uburst 100ms',
                    extractor='generic.max_microburst_100ms.bytes', operation='max',  datatype='bytes')

yui3.TableWidget.create(section, table, 'Microbursts Bytes Summary', width=6)

### Table and Widget 2

t = SharkTable.create(name='Traffic by TCP/UDP', view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                            duration=1, aggregated=False)

create_shark_column(t, 'time', extractor='sample_time', iskey=True, datatype='time', label='Time (ns)')
create_shark_column(t, 'udp_bytes', extractor='udp.bytes', iskey=False, operation='sum', label='UDP Bytes', default_value=0)
create_shark_column(t, 'tcp_bytes', extractor='tcp.bytes', iskey=False, operation='sum', label='TCP Bytes', default_value=0)
yui3.TimeSeriesWidget.create(section, t, 'Traffic By Type (Bytes)', width=12)

