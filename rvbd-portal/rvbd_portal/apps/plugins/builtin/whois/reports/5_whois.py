# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.yui3 as yui3
from rvbd_portal_profiler.datasources.profiler import GroupByTable
from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable

# helper libraries
from rvbd_portal.apps.plugins.builtin.whois.libs.whois import whois

#
# Profiler report
#

report = Report(title="Whois", position=5)
report.save()

section = Section.create(report)

# Define a Table that gets external hosts by avg bytes
table = GroupByTable.create('5-hosts', 'host', duration='1 hour',
                            filterexpr='not srv host 10/8 and not srv host 192.168/16')

Column.create(table, 'host_ip', 'IP Addr', iskey=True)
Column.create(table, 'avg_bytes', 'Avg Bytes', units='s', issortcol=True)


# Create an Analysis table that calls the 'whois' function to craete a link to 'whois'
whoistable = AnalysisTable.create('5-whois-hosts',
                                  tables={'t': table.id},
                                  func=whois)

Column.create(whoistable, 'host_ip', label="IP Addr", iskey=True)
Column.create(whoistable, 'avg_bytes', 'Avg Bytes', datatype='bytes', issortcol=True)
Column.create(whoistable, 'whois', label="Whois link", datatype='html')

yui3.TableWidget.create(section, whoistable, "Link table", width=12)
