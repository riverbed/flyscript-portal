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

#### Customize devices and authorization here

tm08 = Device.objects.get(name="tm08-1")
v10 = Device.objects.get(name="vdorothy10")

#
# Google Map example
#

# Google Map example
report = Report(title="Map", position=4)
report.save()

# Define a table, group by location
dt = Table(name='maploc', module='profiler', device=tm08, duration=60, rows=20,
           filterexpr = 'host 10.99/16',
           options={'groupby': 'host_group'})
dt.save()
Column(table=dt, name='group_name', iskey=True, label = 'Group Name', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label = 'Avg Bytes/s', datatype='bytes', units='B/s', position=2).save()

# Map wdiget on top of that table
wid = Widget(report=report, title="Map",
             row=2, col=2, colwidth=12,
             options = {'key': 'group_name',
                        'value': 'avg_bytes'},
             module="google_maps", uiwidget="MapWidget",
             uioptions = {'minHeight': 500})
wid.save()
wid.tables.add(dt)

