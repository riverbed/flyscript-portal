# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import rvbd_portal.apps.datasource.modules.analysis as analysis
from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.yui3 as yui3

import rvbd_portal_sample.datasources.sample_source as sample

#
# Sample report
#

report = Report(title="Sample")
report.save()

section = Section.create(report)

# Criteria table
table = analysis.create_criteria_table('sample-criteria')
yui3.TableWidget.create(section, table, "Report Criteria", width=12, height=200)

# Define a Overall TimeSeries showing Avg Bytes/s
options=sample.TableOptions(beta=4)
table = sample.Table.create(name='sample-table', duration='15min', resolution='1s',
                            options=options)

Column.create(table, 'time', 'Time', datatype='time', iskey=True)

Column.create(table, 'sin1', 'Sine Wave 1',
              options = sample.ColumnOptions(func='sin', period='5min', alpha=3))
Column.create(table, 'sin2', 'Sine Wave 2',
              options = sample.ColumnOptions(func='sin', period='8min', alpha=5))
Column.create(table, 'cos', 'Cosine Wave',
              options = sample.ColumnOptions(func='cos', period='3min', alpha=2.5))

yui3.TimeSeriesWidget.create(section, table, "Sample Waves", width=12)
