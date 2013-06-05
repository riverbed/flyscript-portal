# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.report.models import Report
from apps.datasource.models import Table, Column
from apps.datasource.models import ColumnOptions
import apps.report.modules.yui3 as yui3

from apps.datasource.modules.tshark import TSharkTable, TableOptions
from apps.datasource.modules.tshark import ColumnOptions as TSharkColumnOptions

import logging
logger = logging.getLogger(__name__)

######################################################################
#
# Financial: App vs Packet
#

report = Report(title="PCAP Analysis")
report.save()

#
# Table: Process Internal.pcap
#

# The pcapfile can be manually specified here as a TableOption:
#   options = TableOptions(pcapfile="/tmp/my.pcap")
# or, on the page enter "pcap /tmp/my.pcp" in the Filter Expression
# box in the Criteria section

# Interesting traces to try:
#   ftp://ita.ee.lbl.gov/new/lbnl.anon-ftp.03-01-10.tcpdump.gz
options = TableOptions()

table = TSharkTable.create('pcap', resolution=60, resample=True,
                           options=options)

Column.create(table, 'pkttime', datatype='time', iskey=True,
              options=TSharkColumnOptions(field='frame.time_epoch'))
Column.create(table, 'iplen', 
              options=TSharkColumnOptions(field='ip.len', fieldtype='int'))
Column.create(table, 'iplen-bits', synthetic=True,
              options=ColumnOptions(compute__expression = '8*{iplen}',
                                     resample__operation = 'sum'))
Column.create(table, 'max-iplen', synthetic=True,
              options=ColumnOptions(compute__expression = '{iplen}',
                                     resample__operation = 'max'))
Column.create(table, 'min-iplen', synthetic=True,
              options=ColumnOptions(compute__expression = '{iplen}',
                                     resample__operation = 'min'))
Column.create(table, 'limit_100', synthetic=True,
              options=ColumnOptions(compute__expression = '100',
                                     resample__operation = 'min'))

# Compute 95th percentile
Column.create(table, 'iplen_95', synthetic=True, label="95%",
              options=ColumnOptions(compute__expression = '{iplen}.quantile(0.95)',
                                    compute__post_resample = True))

# Compute 80th percentile
Column.create(table, 'iplen_80', synthetic=True, label="80%",
              options=ColumnOptions(compute__expression = '{iplen}.quantile(0.80)',
                                    compute__post_resample = True))

# Compute rolling average (EWMA algo)
Column.create(table, 'iplen_ewma', synthetic=True, label="Moving Avg",
              options=ColumnOptions(compute__expression = 'pandas.stats.moments.ewma({iplen}, span=20)',
                                    compute__post_resample = True,
                                    resample__operation = 'sum'))

yui3.TimeSeriesWidget.create(report, table, "IP Bytes over Time", width=12, height=400,
                             cols = ['iplen', 'iplen_95', 'iplen_80', 'iplen_ewma'])

