# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.datasource.models import Column

import rvbd_portal.apps.report.modules.yui3 as yui3

from rvbd_portal_wireshark.datasources.wireshark import WireSharkTable
from rvbd_portal_wireshark.datasources.wireshark import ColumnOptions as WireSharkColumnOptions

import logging
logger = logging.getLogger(__name__)

######################################################################
#
# Financial: App vs Packet
#

report = Report(title="PCAP Analysis (FileField)", position=8)
report.save()

section = Section.create(report)


#
# Table: Process Internal.pcap
#

table = WireSharkTable.create('pcap', resample=True,
                              resolution='1s', resolutions=['1s','1m'])

Column.create(table, 'pkttime', datatype='time', iskey=True,
              options=WireSharkColumnOptions(field='frame.time_epoch'))
Column.create(table, 'iplen', 
              options=WireSharkColumnOptions(field='ip.len', fieldtype='int'))
Column.create(table, 'iplen-bits', synthetic=True,
              compute_expression='8*{iplen}',
              resample_operation='sum')

Column.create(table, 'max-iplen', synthetic=True,
              compute_expression='{iplen}',
              resample_operation='max')
Column.create(table, 'min-iplen', synthetic=True,
              compute_expression='{iplen}',
              resample_operation='min')
Column.create(table, 'limit_100', synthetic=True,
              compute_expression='100',
              resample_operation='min')

# Compute 95th percentile
Column.create(table, 'iplen_95', synthetic=True, label="95%",
              compute_expression='{iplen}.quantile(0.95)',
              compute_post_resample=True)

# Compute 80th percentile
Column.create(table, 'iplen_80', synthetic=True, label="80%",
              compute_expression='{iplen}.quantile(0.80)',
              compute_post_resample=True)

# Compute rolling average (EWMA algo)
Column.create(table, 'iplen_ewma', synthetic=True, label="Moving Avg",
              compute_expression='pandas.stats.moments.ewma({iplen}, span=20)',
              compute_post_resample=True)

yui3.TimeSeriesWidget.create(section, table, "IP Bytes over Time", width=12, height=400,
                             cols=['iplen', 'iplen_95', 'iplen_80', 'iplen_ewma'])
