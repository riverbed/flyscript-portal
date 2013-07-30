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

#### Load devices that are defined
PROFILER = Device.objects.get(name="profiler")

INTERFACE = '10.99.16.252:2'


report = Report(title="QoS Report Auto Resolution", position=16)
report.save()

# Define a Overall TimeSeries showing In/Out Utilization
table = TimeSeriesTable.create('qos-overall-util', PROFILER, duration=15*60, 
                               interface=True, datafilter='interfaces_a,10.99.16.252:2')

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_util', 'Avg Inbound Util %', datatype='bytes', units='B/s')
Column.create(table, 'out_avg_util', 'Avg Outbound Util %', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "Overall Utilization", width=12)

# Define a Overall TimeSeries showing In/Out Totals
table = TimeSeriesTable.create('qos-overall-total', PROFILER, duration=15*60, 
                               interface=True, datafilter='interfaces_a,10.99.16.252:2')

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_total_bytes', 'Total Inbound Bytes', datatype='bytes', units='B/s')
Column.create(table, 'out_total_bytes', 'Total Outbound Bytes', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "Overall In/Out Bandwidth", width=6)


# Define a Overall TimeSeries showing In/Out Totals
table = TimeSeriesTable.create('qos-overall-avg', PROFILER, duration=15*60, 
                               interface=True, datafilter='interfaces_a,10.99.16.252:2')

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_bytes', 'Avg Inbound Bytes/s', datatype='bytes', units='B/s')
Column.create(table, 'out_avg_bytes', 'Avg Outbound Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "Overall Average In/Out Bandwidth", width=6)

###
# QOS Summary Tables
table = GroupByTable.create('qos-inbound-totals', PROFILER, groupby='qos', duration=15*60,
                            interface=True,
                            filterexpr='inbound interface 10.99.16.252:2')
Column.create(table, 'qos', 'QoS', iskey=True)
Column.create(table, 'qos_name', 'QoS Name', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')
Column.create(table, 'total_bytes', 'Total Bytes/s', datatype='bytes', units='B/s')
Column.create(table, 'avg_util', 'Avg Util', datatype='metric')
Column.create(table, 'peak_util', 'Peak Util', datatype='metric')

yui3.TableWidget.create(report, table, "Inbound Traffic by QoS", width=6)

table = GroupByTable.create('qos-outbound-totals', PROFILER, groupby='qos', duration=15*60,
                            interface=True,
                            filterexpr='outbound interface 10.99.16.252:2')
Column.create(table, 'qos', 'QoS', iskey=True)
Column.create(table, 'qos_name', 'QoS Name', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')
Column.create(table, 'total_bytes', 'Total Bytes/s', datatype='bytes', units='B/s')
Column.create(table, 'avg_util', 'Avg Util', datatype='metric')
Column.create(table, 'peak_util', 'Peak Util', datatype='metric')

yui3.TableWidget.create(report, table, "Outbound Traffic by QoS", width=6)

###
# QOS Tables
QOS = 'AF11'
table = TimeSeriesTable.create('qos-inbound-%s' % QOS.lower(), PROFILER, duration=15*60,
                               interface=True,
                               datafilter='interfaces_a,10.99.16.252:2',
                               filterexpr='inbound interface 10.99.16.252:2 and qos %s' % QOS)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "%s: Average Inbound Bandwidth" % QOS, width=6)

# Define a Overall TimeSeries showing In/Out Totals
QOS = 'AF11'
table = TimeSeriesTable.create('qos-outbound-%s' % QOS.lower(), PROFILER, duration=15*60,
                               interface=True,
                               datafilter='interfaces_a,10.99.16.252:2',
                               filterexpr='outbound interface 10.99.16.252:2 and qos %s' % QOS)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "%s: Average Outbound Bandwidth" % QOS, width=6)


# QOS Tables
QOS = 'EF'
table = TimeSeriesTable.create('qos-inbound-%s' % QOS.lower(), PROFILER, duration=15*60,
                               interface=True,
                               datafilter='interfaces_a,10.99.16.252:2',
                               filterexpr='inbound interface 10.99.16.252:2 and qos %s' % QOS)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "%s: Average Inbound Bandwidth" % QOS, width=6)

# Define a Overall TimeSeries showing In/Out Totals
QOS = 'EF'
table = TimeSeriesTable.create('qos-outbound-%s' % QOS.lower(), PROFILER, duration=15*60,
                               interface=True,
                               datafilter='interfaces_a,10.99.16.252:2',
                               filterexpr='outbound interface 10.99.16.252:2 and qos %s' % QOS)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "%s: Average Outbound Bandwidth" % QOS, width=6)


# QOS Tables
QOS = 'Default'
table = TimeSeriesTable.create('qos-inbound-%s' % QOS.lower(), PROFILER, duration=15*60,
                               interface=True,
                               datafilter='interfaces_a,10.99.16.252:2',
                               filterexpr='inbound interface 10.99.16.252:2 and qos %s' % QOS)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "%s: Average Inbound Bandwidth" % QOS, width=6)

# Define a Overall TimeSeries showing In/Out Totals
QOS = 'Default'
table = TimeSeriesTable.create('qos-outbound-%s' % QOS.lower(), PROFILER, duration=15*60,
                               interface=True,
                               datafilter='interfaces_a,10.99.16.252:2',
                               filterexpr='outbound interface 10.99.16.252:2 and qos %s' % QOS)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(report, table, "%s: Average Outbound Bandwidth" % QOS, width=6)
