from django import forms

from apps.datasource.forms import fields_add_time_selection
from apps.datasource.modules.analysis import AnalysisTable
from apps.datasource.models import TableField, Table, Column
from libs.fields import Function

from apps.report.models import Report, Section
from apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Post Process' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

TableField.create('w', 'W Value', section)
TableField.create('x', 'X Value', section)
TableField.create('y', 'Y Value', section)

for (f1,f2) in [('w', 'x'), ('w', 'y'), ('x', 'y')]:
    ( TableField.create
      ('%s%s' % (f1, f2), '%s+%s Value' % (f1, f2), section,
       hidden = True, parents=[f1, f2],
       post_process_func = Function(funcs.postprocess_field_compute,
                                    params={'fields': [f1, f2]})))
    
table = AnalysisTable.create('test-criteria-postprocess', tables={}, duration=60,
                             func = funcs.criteria)
Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table')
