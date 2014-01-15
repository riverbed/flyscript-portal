# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from rvbd_common.apps.datasource.models import Column, TableField
from rvbd_common.apps.report.models import Report, Section
import rvbd_common.apps.report.modules.yui3 as yui3
from rvbd_common.apps.datasource.modules import profiler
from rvbd_common.apps.datasource.modules.profiler import GroupByTable, TimeSeriesTable

report = Report(title="QoS Report", position=15)
report.save()

interface_field = TableField.create(keyword='interface', label='Interface', required=True)
datafilter_field = TableField.create(keyword='datafilter', hidden=True,
                                     post_process_template='interfaces_a,{interface}')

section = Section.create(report, title="Overall")

# Define a Overall TimeSeries showing In/Out Utilization
table = TimeSeriesTable.create('qos-overall-util', 
                               duration=15, resolution=60,
                               interface=True)
table.fields.add(interface_field)
table.fields.add(datafilter_field)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_util', 'Avg Inbound Util %', datatype='bytes', units='B/s')
Column.create(table, 'out_avg_util', 'Avg Outbound Util %', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(section, table, "Overall Utilization", width=12)

# Define a Overall TimeSeries showing In/Out Totals
table = TimeSeriesTable.create('qos-overall-total', 
                               duration=15, resolution=15*60,
                               interface=True)
table.fields.add(interface_field)
table.fields.add(datafilter_field)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_total_bytes', 'Total Inbound Bytes', datatype='bytes', units='B/s')
Column.create(table, 'out_total_bytes', 'Total Outbound Bytes', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(section, table, "Overall In/Out Bandwidth", width=6)

# Define a Overall TimeSeries showing In/Out Totals
table = TimeSeriesTable.create('qos-overall-avg', 
                               duration=15, resolution=60,
                               interface=True)
table.fields.add(interface_field)
table.fields.add(datafilter_field)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_bytes', 'Avg Inbound Bytes/s', datatype='bytes', units='B/s')
Column.create(table, 'out_avg_bytes', 'Avg Outbound Bytes/s', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(section, table, "Overall Average In/Out Bandwidth", width=6)

###
# QOS Summary Tables
for direction in ['inbound', 'outbound']:
    table = GroupByTable.create('qos-%s-totals' % direction, groupby='qos', 
                                duration=15, resolution=60,
                                interface=True)
    table.fields.add(interface_field)
    TableField.create(keyword='%s_filterexpr' % direction, obj=table, hidden=True, 
                      post_process_template='%s interface {interface}' % direction)
    profiler.fields_add_filterexprs_field(table, '%s_filterexpr' % direction)

    Column.create(table, 'qos', 'QoS', iskey=True)
    Column.create(table, 'qos_name', 'QoS Name', iskey=True)
    Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')
    Column.create(table, 'total_bytes', 'Total Bytes/s', datatype='bytes', units='B/s')
    Column.create(table, 'avg_util', 'Avg Util', datatype='metric')
    Column.create(table, 'peak_util', 'Peak Util', datatype='metric')

    yui3.TableWidget.create(section, table, "%s Traffic by QoS" % direction.capitalize(), width=6)

###
# QoS sections, defaults to AF11, EF, and Default
for i,qos in enumerate(['AF11', 'EF', 'Default']):
    
    section = Section.create(report, title="QoS %d" % i)

    ###
    # QOS Tables

    for direction in ['inbound', 'outbound']:
        table = TimeSeriesTable.create('qos-%d-%s' % (i, direction), 
                                       duration=15, resolution=60,
                                       interface=True)
        table.fields.add(interface_field)
        table.fields.add(datafilter_field)
        qos_field = TableField.create(keyword='qos_%d' % i, label='QoS %d (DSCP)' % i, obj=table, initial=qos)
        TableField.create(keyword='%s_filterexpr' % direction, obj=table, hidden=True, 
                          post_process_template='%s interface {interface} and qos {qos_%d}' % (direction, i))
        profiler.fields_add_filterexprs_field(table, '%s_filterexpr' % direction)

        Column.create(table, 'time', 'Time', datatype='time', iskey=True)
        Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

        yui3.TimeSeriesWidget.create(section, table, "QoS {qos_%d} - Average %s Bandwidth" % (i, direction.capitalize()), width=6)

