# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.yui3 as yui3

from rvbd_portal_sharepoint.datasources.sharepoint import (SharepointTable,
                                                           create_sharepoint_column)
#
# Profiler report
#

report = Report(title="Sharepoint", position=2)
report.save()

section = Section.create(report)


# Define a Sharepoint Table
table = SharepointTable.create('sp-documents', '/', 'Shared Documents')

create_sharepoint_column(table, 'BaseName', issortcol=True)
create_sharepoint_column(table, 'Created', datatype='time')
create_sharepoint_column(table, 'Modified', datatype='time')
create_sharepoint_column(table, 'ID')
create_sharepoint_column(table, 'EncodedAbsUrl')

yui3.TableWidget.create(section, table, "Sharepoint Documents List",
                        height=300, width=12)
