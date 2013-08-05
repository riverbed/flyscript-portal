# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ('License').  
# This software is distributed 'AS IS' as set forth in the License.

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

from apps.datasource.models import Column
from apps.devices.models import Device
from apps.report.models import Report
import apps.report.modules.yui3 as yui3
from apps.datasource.modules.profiler import GroupByTable, TimeSeriesTable
from apps.datasource.modules.shark import SharkTable, create_shark_column

#### Load devices that are defined
SHARK1 = Device.objects.get(name='shark1')

### Configure Shark View To Use

SHARK_VIEW_NAME = 'jobs/flyscript-portal'       # Note: must prefix job names with 'jobs/'
SHARK_VIEW_SIZE = '10%'                         # Default size to use if job does not already exist


#
# Define a Shark Report and Table
#
report = Report(title='Shark DNS', position=6)
report.save()


### DNS Success/Failure Queries Over time
name = 'DNS Success and Failure Queries Over Time' 
t = SharkTable.create(name=name, device=SHARK1, view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                      duration=10, resolution=60, aggregated=False)

create_shark_column(t, 'time', label='Time', iskey=True, datatype='time', extractor='sample_time')
create_shark_column(t, 'dns_count', label='DNS Query Count', iskey=False, extractor='dns.query.count', operation='sum')
create_shark_column(t, 'dns_is_success', label='DNS Success', iskey=False, extractor='dns.is_success', operation='none')
yui3.TimeSeriesWidget.create(report, t, name, width=12)


### DNS Response Code List for Shark 1
name = 'DNS Response Codes'
table = SharkTable.create(name=name, device=SHARK1, view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                      duration=10, aggregated=True)

create_shark_column(table, 'dns_is_success_str', label='DNS Success', iskey=True, extractor='dns.is_success_str', operation='none')
create_shark_column(table, 'dns_total_queries', label='DNS Total Queries', issortcol=True, extractor='dns.query.count', operation='sum')

yui3.PieWidget.create(report, table, name, width=6)

### DNS Query Type for Shark 1
name = 'DNS Query Type'
table = SharkTable.create(name=name, device=SHARK1, view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                      duration=10, aggregated=True)

create_shark_column(table, 'dns_query_type', label='DNS Query Type', iskey=True, extractor='dns.query.type', operation='none')
create_shark_column(table, 'dns_total_queries', label='DNS Total Queries', issortcol=True, extractor='dns.query.count', operation='sum')

yui3.PieWidget.create(report, table, name, width=6)

### DNS Request Details Table for Shark 1
name = 'DNS Requests'
table = SharkTable.create(name=name, device=SHARK1, view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                      duration=10, aggregated=True)

create_shark_column(table, 'dns_query_name', label='DNS Request', iskey=True, extractor='dns.query.name', issortcol=True)
create_shark_column(table, 'dns_query_type', label='# Requests', iskey=False, extractor='dns.query.count', operation='sum')
create_shark_column(table, 'dns_is_success', label='# Successful', iskey=False, extractor='dns.is_success', operation='none')

yui3.TableWidget.create(report, table, name, width=12)

### Response Time over Time
name = 'DNS Response Time Over Time'
t = SharkTable.create(name=name, device=SHARK1, view=SHARK_VIEW_NAME, view_size=SHARK_VIEW_SIZE,
                      duration=10, resolution=60, aggregated=False)

create_shark_column(t, 'time', label='Time', iskey=True, datatype='time', extractor='sample_time', operation='none')
create_shark_column(t, 'dns_response_time', label='DNS Response Time (ns)', iskey=False, extractor='dns.response_time', operation='none')

yui3.TimeSeriesWidget.create(report, t, name, width=12)


