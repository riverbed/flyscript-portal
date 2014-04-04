from django import forms

from rvbd_portal.apps.datasource.forms import fields_add_time_selection
from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Table, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Two Reports - 1')
report.save()

# Section
section = Section.create(report=report, title='Section')
section.save()

# Table
table = AnalysisTable.create('test-criteria-tworeports-1', tables={},
                             func = funcs.analysis_echo_criteria)
TableField.create(keyword='k1', label='Key 1', obj=table, initial='r1')

Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table 1')
