# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging

from django.templatetags.static import static
from django.core.urlresolvers import reverse

from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.datasource.modules.html import StaticHTMLTable
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.raw as raw
import rvbd_portal.apps.report.modules.maps as maps
import rvbd_portal.apps.report.modules.yui3 as yui3
from rvbd_portal_profiler.datasources.profiler import GroupByTable
from rvbd_portal_sharepoint.datasources.sharepoint import (SharepointTable,
                                                           create_sharepoint_column)


logger = logging.getLogger(__name__)

#
# HTML Example Report
#

report = Report(title="Landing Page Example", position=1, hide_criteria=True,
                reload_minutes=5)
report.save()

section = Section.create(report, title='Raw HTML')


# Define an image
imgurl = 'http://radar.weather.gov/Conus/Loop/NatLoop_Small.gif'
html = '<img src="%s" alt="Doppler Radar National Mosaic Loop">' % imgurl

table = StaticHTMLTable.create('Weather Image', html)
raw.TableWidget.create(section, table, 'weather image', width=6)


# Define an html table of links
# As an example of how the module loading works, this table
# may end up being shorter than the actual total number of reports
# because at the time this is calculated, all the remaining reports
# may not yet be in the database.
lines = []
reports = Report.objects.all().order_by('position')
for r in reports:
    kwargs = {'report_slug': r.slug,
              'namespace': r.namespace}

    url = reverse('report-view', kwargs=kwargs)
    line = '<li><a href="%s" target="_blank">%s</a></li>' % (url, r.title)
    lines.append(line)

html = """
<ul>
%s
</ul>
""" % '\n'.join(lines)

table = StaticHTMLTable.create('Report Links', html)
raw.TableWidget.create(section, table, 'report table', width=6)


# Define a map and table, group by location
table = GroupByTable.create('maploc', 'host_group', duration=60, resolution='auto')

Column.create(table, 'group_name',    label='Group Name', iskey=True)
Column.create(table, 'response_time', label='Resp Time',  datatype='metric')
Column.create(table, 'network_rtt',   label='Net RTT',    datatype='metric')
Column.create(table, 'server_delay',  label='Srv Delay',  datatype='metric')

maps.MapWidget.create(section, table, "Response Time", width=5, height=300)


# Define a Sharepoint Table
table = SharepointTable.create('sp-documents', '/', 'Shared Documents')

create_sharepoint_column(table, 'BaseName', issortcol=True)
create_sharepoint_column(table, 'Created', datatype='time')
create_sharepoint_column(table, 'Modified', datatype='time')
create_sharepoint_column(table, 'ID')
create_sharepoint_column(table, 'EncodedAbsUrl')

yui3.TableWidget.create(section, table, "Sharepoint Documents List",
                        height=300, width=7)
