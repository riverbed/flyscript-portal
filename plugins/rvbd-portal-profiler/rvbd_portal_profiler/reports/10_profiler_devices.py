# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.yui3 as yui3

from rvbd_portal_profiler.datasources.profiler_devices import DevicesTable

report = Report(title="Profiler Device List", position=10)
report.save()

section = Section.create(report)

#
# Device Table

devtable = DevicesTable.create('devtable')
Column.create(devtable, 'ipaddr', 'Device IP', iskey=True, isnumeric=False)
Column.create(devtable, 'name', 'Device Name', isnumeric=False)
Column.create(devtable, 'type', 'Flow Type', isnumeric=False)
Column.create(devtable, 'version', 'Flow Version', isnumeric=False)

yui3.TableWidget.create(section, devtable, "Device List", height=300, width=12)

