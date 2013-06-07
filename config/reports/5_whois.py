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
from apps.report.models import Report
import apps.report.modules.yui3 as yui3
from apps.datasource.modules.profiler import GroupByTable, TimeSeriesTable
from apps.datasource.modules.analysis import AnalysisTable

#### Load devices that are defined
PROFILER = Device.objects.get(name="profiler")

#
# Profiler report
#

report = Report(title="Whois", position=5)
report.save()

# Define a Table that gets external hosts by avg bytes
table = GroupByTable.create('5-hosts', PROFILER, 'host', duration=60*10,
                            filterexpr='not srv host 10/8 and not srv host 192.168/16')

Column.create(table, 'host_ip', 'IP Addr', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes', units='s', issortcol=True)

from config.reports.helpers.whois import whois

# Create an Analysis table that calls the 'whois' function to craete a link to 'whois'
whoistable = AnalysisTable.create('5-whois-hosts',
                                  tables = {'t' : table.id},
                                  func = whois)

Column.create(whoistable, 'host_ip', label="IP Addr", iskey=True)
Column.create(whoistable, 'avg_bytes', 'Avg Bytes', datatype='bytes', issortcol=True)
Column.create(whoistable, 'whois', label="Whois link", datatype='html')

yui3.TableWidget.create(report, whoistable, "Link table", width=12)

