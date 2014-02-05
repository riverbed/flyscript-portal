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

from rvbd_portal.apps.datasource.modules.html import StaticHTMLTable
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.raw as raw


logger = logging.getLogger(__name__)

#
# HTML Example Report
#

report = Report(title="HTML Example", position=1)
report.save()

section = Section.create(report, title='Raw HTML')


# Define an image
imgurl = 'http://radar.weather.gov/Conus/Loop/NatLoop_Small.gif'
html = '<img src="%s" alt="Doppler Radar National Mosaic Loop">' % imgurl

table = StaticHTMLTable.create('Weather Image', html)
raw.TableWidget.create(section, table, 'weather image')


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
raw.TableWidget.create(section, table, 'report table')
