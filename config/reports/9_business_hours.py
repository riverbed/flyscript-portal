# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import Column
from apps.devices.models import Device
from apps.report.models import Report
import apps.report.modules.yui3 as yui3
from apps.datasource.modules.profiler import GroupByTable, TimeSeriesTable
from apps.datasource.modules.analysis import  AnalysisTable
from apps.datasource.modules.profiler_devices import DevicesTable
import libs.business_hours as bizhours
import libs.profiler_tools as protools

PROFILER = Device.objects.get(name="profiler")

report = Report(title="Business Hour Reporting - Profiler Interfaces", position=0)
report.save()

bizhours.add_criteria(report)

#
# Define by-interface table from Profiler
#
basetable = GroupByTable.create('bh-basetable', PROFILER, 'interface', duration=60,
                                resolution=3600, interface=True)

# Define all of your columns here associated with basetable
# For each data column (iskey=False), you must specify the aggreation method
# in the bizhours.create below.
Column.create(basetable, 'interface_dns', 'Interface', iskey=True, isnumeric=False)
Column.create(basetable, 'avg_util', '% Utilization', datatype='pct', issortcol=True) 
Column.create(basetable, 'in_avg_util', '% Utilization In', datatype='pct', issortcol=False)
Column.create(basetable, 'out_avg_util', '% Utilization Out', datatype='pct', issortcol=False)

# The 'aggregate' parameter describes how similar rows on different business days
# should be combined.  For example:
#
#     Day    Total Bytes   Avg Bytes/s
# ---------  ------------  -----------
#     Mon    28MB            100            
#     Tue    56MB            200            
# ========== ============= ===========
# Combined   84MB            150
# Method     sum             avg
#
# Common methods:
#   sum    - just add up all the data, typical for totals
#   avg    - compute the average (using time as a weight), for anything "average"
#   min    - minimum of all values
#   max    - maximum of all values
#
bustable_pre = bizhours.create('bh-bustable-pre', basetable, 
                               aggregate = { 'avg_util' : 'avg',
                                             'in_avg_util' : 'avg',
                                             'out_avg_util' : 'avg' },
                               resolution=3600, duration=60*24*7, cacheable=False)

#bustable = AnalysisTable.create('bh-bustable', tables={'table': bustable_pre.id},
#                                func = protools.process_interface_dns)


# Device Table

devtable = DevicesTable.create('devtable', PROFILER)
Column.create(devtable, 'ipaddr', 'Device IP', iskey=True, isnumeric=False)
Column.create(devtable, 'name', 'Device Name', isnumeric=False)
Column.create(devtable, 'type', 'Flow Type', isnumeric=False)
Column.create(devtable, 'version', 'Flow Version', isnumeric=False)

bustable = AnalysisTable.create('bh-bustable', tables={'devices': devtable.id,
                                                       'traffic': bustable_pre.id},
                                func = protools.process_join_ip_device)

Column.create(bustable, 'interface_name', 'Interface', iskey=True, isnumeric=False)
bustable.copy_columns(bustable_pre, except_columns=['interface_dns'])

yui3.TableWidget.create(report, bustable, "Interface", height=600)
yui3.BarWidget.create(report, bustable, "Interface Utilization", height=600, valuecols=['avg_util'])
yui3.TableWidget.create(report, bizhours.timestable(), "Covered times", width=12, height=200)

