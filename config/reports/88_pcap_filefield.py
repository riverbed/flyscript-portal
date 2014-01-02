# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from django import forms

from apps.report.models import Report, Section
from apps.datasource.models import Table, Column, TableField
import apps.report.modules.yui3 as yui3

from apps.datasource.modules.tshark import TSharkTable, TableOptions
from apps.datasource.modules.tshark import ColumnOptions as TSharkColumnOptions

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

# The pcapfile can be manually specified here as a TableOption:
#   options = TableOptions(pcapfile="/tmp/my.pcap")
# or, on the page enter "pcap /tmp/my.pcp" in the Filter Expression
# box in the Criteria section

# Interesting traces to try:
#   ftp://ita.ee.lbl.gov/new/lbnl.anon-ftp.03-01-10.tcpdump.gz
options = TableOptions()

table = TSharkTable.create('pcap', resolution=60, resample=True,
                           options=options)
filefield = TableField(keyword='pcapfile',
                       label='PCAP File',
                       field_cls=forms.FileField)
filefield.save()
table.fields.add(filefield)

Column.create(table, 'pkttime', datatype='time', iskey=True,
              options=TSharkColumnOptions(field='frame.time_epoch'))
Column.create(table, 'iplen', 
              options=TSharkColumnOptions(field='ip.len', fieldtype='int'))
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
