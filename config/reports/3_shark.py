# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import *
from apps.report.models import *
from apps.geolocation.models import *
from apps.datasource.modules.shark import ColumnOptions as shark_ColumnOptions
import apps.report.modules.yui3 as yui3

#### Customize devices and authorization here

tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Define a Shark Report and Table
#
report = Report(title="Shark", position=3)
report.save()

table = Table(name='Packet Traffic', module='shark', device=v10, duration=10,
           options={'view': 'jobs/Flyscript-tests-job',
                    })
table.save()
Column(table=table, name='ip_src', iskey=True, label='Source IP', position=1,
       options=shark_ColumnOptions(extractor='ip.src').__dict__).save()
Column(table=table, name='ip_dst', iskey=True, label='Dest IP', position=2,
       options=shark_ColumnOptions(extractor='ip.dst').__dict__).save()
Column(table=table, name='generic_packets', iskey=False, label='Packets', position=3,
       options=shark_ColumnOptions(extractor='generic.packets', operation='sum').__dict__).save()

yui3.TableWidget.create(report, table, "Shark Packets (last 10 minutes)", width=12)

"""
table = Table(name='MicroburstsTotal', module='shark', duration=10,
           options={
                    'aggregated': True,
                    'view': 'jobs/Flyscript-tests-job',
                    })
table.save()
table.add_columns([
     'max_microburst_1ms_packets',
     'max_microburst_10ms_packets',
     'max_microburst_100ms_packets',
])
wid = Widget(report=report, title="Microburst Packets (last 10 minutes)",
             row=2, col=1, rows=1000, width=12,
             module="yui3", uiwidget="TableWidget", uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(table)

table = Table(name='MicroburstsTime', module='shark', duration=10,
           options={
                    'aggregated': False,
                    'view': 'jobs/Flyscript-tests-job',
           })

table.save()
table.add_columns([
    'time',
    'max_microburst_1ms_packets',
#    'max_microburst_10ms_packets',
#    'max_microburst_100ms_packets',
    ])
wid = Widget(report=report, title="Microburst Packets Timeseries (last 10 minutes)",
             row=3, col=1, rows=1000, width=12,
             options={'axes': {'0': {'title': 'pkts/ms',
                                     'position': 'left',
                                     'columns': ['max_microburst_1ms_packets']}
             }},
             module="yui3", uiwidget="TimeSeriesWidget", uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(table)
#
"""
