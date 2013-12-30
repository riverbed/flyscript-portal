# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import Column, TableField
from apps.devices.models import Device
from apps.report.models import Report, Section
import apps.report.modules.yui3 as yui3
from apps.datasource.modules.profiler import GroupByTable, TimeSeriesTable
from apps.datasource.modules.profiler import fields_add_combine_filterexprs

#### Replace the following value with the WAN interface for this report to monitor
INTERFACE = '10.99.16.252:2'

#### Load devices that are defined
PROFILER = Device.objects.get(name="profiler")

# User visible criteria:
#   wan_interface
#
# This is then used by two different tables:
#   table 1:
#     filterexpr = inbound interface <wan_interface>
#     datafilter = interfaces_a,<wan_interface>
#   table 2:
#     filterexpr = outbound interface <wan_interface>
#     datafilter = interfaces_a,<wan_interface>
#

report = Report(title="QoS Criteria Report", position=55)
report.save()

wan_interface = TableField(keyword='wan_interface',
                           label='WAN Interface')
wan_interface.save()
report.fields.add(wan_interface)

section = Section.create(report)

if 0:
    table_criteria_inbound = TableField(keyword='filterexpr',
                                        template='inbound interface {0}',
                                        label='WAN Inbound Interface',
                                        initial=INTERFACE)
    table_criteria_inbound.save()

    table_criteria_outbound = TableField(keyword='filterexpr',
                                         template='outbound interface {0}',
                                         label='WAN Outbound Interface',
                                         initial=INTERFACE)
    table_criteria_outbound.save()

# Define a Overall TimeSeries showing In/Out Utilization
table = TimeSeriesTable.create('qos-overall-util', PROFILER,
                               duration=15*60, resolution=15*60,
                               interface=True)

wan_inbound = TableField(keyword='wan_filterexpr',
                         template='inbound interface {wan_interface}',
                         label='WAN Inbound Interface',
                         hidden=True)
wan_inbound.save()
wan_inbound.parents.add(wan_interface)

table.fields.add(wan_inbound)

fields_add_combine_filterexprs(table, parents=[wan_inbound])

Column.create(table, 'time', 'Time', datatype='time', iskey=True)
Column.create(table, 'in_avg_util', 'Avg Inbound Util %', datatype='bytes', units='B/s')
Column.create(table, 'out_avg_util', 'Avg Outbound Util %', datatype='bytes', units='B/s')

yui3.TimeSeriesWidget.create(section, table, "Overall Utilization", width=12)

if 0:

    ###
    # QOS Summary Tables
    table = GroupByTable.create('qos-inbound-totals', PROFILER, groupby='qos',
                                duration=15*60, resolution=15*60,
                                interface=True,
                                filterexpr='inbound interface %s' % INTERFACE)
    table.criteria.add(table_criteria_inbound)

    Column.create(table, 'qos', 'QoS', iskey=True)
    Column.create(table, 'qos_name', 'QoS Name', iskey=True)
    Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')
    Column.create(table, 'total_bytes', 'Total Bytes/s', datatype='bytes', units='B/s')
    Column.create(table, 'avg_util', 'Avg Util', datatype='metric')
    Column.create(table, 'peak_util', 'Peak Util', datatype='metric')

    yui3.TableWidget.create(section, table, "Inbound Traffic by QoS", width=6)

    table = GroupByTable.create('qos-outbound-totals', PROFILER, groupby='qos',
                                duration=15*60, resolution=15*60,
                                interface=True,
                                filterexpr='outbound interface %s' % INTERFACE)
    table.criteria.add(table_criteria_outbound)

    Column.create(table, 'qos', 'QoS', iskey=True)
    Column.create(table, 'qos_name', 'QoS Name', iskey=True)
    Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')
    Column.create(table, 'total_bytes', 'Total Bytes/s', datatype='bytes', units='B/s')
    Column.create(table, 'avg_util', 'Avg Util', datatype='metric')
    Column.create(table, 'peak_util', 'Peak Util', datatype='metric')

    yui3.TableWidget.create(section, table, "Outbound Traffic by QoS", width=6)

    ###
    # QOS Tables

    QOS = 'EF'
    table = TimeSeriesTable.create('qos-inbound-%s' % QOS.lower(), PROFILER,
                                   duration=15*60, resolution=15*60,
                                   interface=True,
                                   datafilter='interfaces_a,%s' % INTERFACE,
                                   filterexpr='inbound interface %s and qos %s' % (INTERFACE, QOS))

    table_criteria_inbound_qos = TableField(keyword='filterexpr',
                                                   template='inbound interface {0} and qos %s' % QOS,
                                                   label='WAN %s Inbound Interface' % QOS,
                                                   initial=INTERFACE)
    table_criteria_inbound_qos.save()
    table.criteria.add(table_criteria_inbound_qos)

    Column.create(table, 'time', 'Time', datatype='time', iskey=True)
    Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

    yui3.TimeSeriesWidget.create(section, table, "%s: Average Inbound Bandwidth" % QOS, width=6)

    # Define a Overall TimeSeries showing In/Out Totals
    QOS = 'EF'
    table = TimeSeriesTable.create('qos-outbound-%s' % QOS.lower(), PROFILER,
                                   duration=15*60, resolution=15*60,
                                   interface=True,
                                   datafilter='interfaces_a,%s' % INTERFACE,
                                   filterexpr='outbound interface %s and qos %s' % (INTERFACE, QOS))

    table_criteria_outbound_qos = TableField(keyword='filterexpr',
                                                    template='outbound interface {0} and qos %s' % QOS,
                                                    label='WAN %s Outbound Interface' % QOS,
                                                    initial=INTERFACE)
    table_criteria_outbound_qos.save()
    table.criteria.add(table_criteria_outbound_qos)

    Column.create(table, 'time', 'Time', datatype='time', iskey=True)
    Column.create(table, 'avg_bytes', 'Avg Bytes/s', datatype='bytes', units='B/s')

    yui3.TimeSeriesWidget.create(section, table, "%s: Average Outbound Bandwidth" % QOS, width=6)

