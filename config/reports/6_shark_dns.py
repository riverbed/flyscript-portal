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
from rvbd_common.apps.datasource.modules.shark import SharkTable, create_shark_column

#
# Define a Shark Report and Table
#
report = Report(title='Shark DNS', position=6)
report.save()

section = Section.create(report)


### DNS Success/Failure Queries Over time
name = 'DNS Success and Failure Queries Over Time' 
t = SharkTable.create(name=name, 
                      duration=15, resolution='1min', aggregated=False)

create_shark_column(t, 'time', label='Time', iskey=True, datatype='time', extractor='sample_time')
create_shark_column(t, 'dns_count', label='DNS Query Count', iskey=False, extractor='dns.query.count', operation='sum')
create_shark_column(t, 'dns_is_success', label='DNS Success', iskey=False, extractor='dns.is_success', operation='none')
yui3.TimeSeriesWidget.create(section, t, name, width=12)


### DNS Response Code List for Shark 1
name = 'DNS Response Codes'
table = SharkTable.create(name=name, 
                      duration=15, aggregated=True)

create_shark_column(table, 'dns_is_success_str', label='DNS Success', iskey=True, extractor='dns.is_success_str', operation='none')
create_shark_column(table, 'dns_total_queries', label='DNS Total Queries', issortcol=True, extractor='dns.query.count', operation='sum')

yui3.PieWidget.create(section, table, name, width=6)

### DNS Query Type for Shark 1
name = 'DNS Query Type'
table = SharkTable.create(name=name, 
                      duration=15, aggregated=True)

create_shark_column(table, 'dns_query_type', label='DNS Query Type', iskey=True, extractor='dns.query.type', operation='none')
create_shark_column(table, 'dns_total_queries', label='DNS Total Queries', issortcol=True, extractor='dns.query.count', operation='sum')

yui3.PieWidget.create(section, table, name, width=6)

### DNS Request Details Table for Shark 1
name = 'DNS Requests'
table = SharkTable.create(name=name, 
                      duration=15, aggregated=True)

create_shark_column(table, 'dns_query_name', label='DNS Request', iskey=True, extractor='dns.query.name', issortcol=True)
create_shark_column(table, 'dns_query_type', label='# Requests', iskey=False, extractor='dns.query.count', operation='sum')
create_shark_column(table, 'dns_is_success', label='# Successful', iskey=False, extractor='dns.is_success', operation='none')

yui3.TableWidget.create(section, table, name, width=12)

### Response Time over Time
name = 'DNS Response Time Over Time'
t = SharkTable.create(name=name, 
                      duration=15, resolution='1min', aggregated=False)

create_shark_column(t, 'time', label='Time', iskey=True, datatype='time', extractor='sample_time', operation='none')
create_shark_column(t, 'dns_response_time', label='DNS Response Time (ns)', iskey=False, extractor='dns.response_time', operation='none')

yui3.TimeSeriesWidget.create(section, t, name, width=12)


