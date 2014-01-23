from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from rvbd_portal.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Post Process' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

table = AnalysisTable.create('test-criteria-postprocess', tables={}, 
                             func = funcs.analysis_echo_criteria)

TableField.create('w', 'W Value', table)
TableField.create('x', 'X Value', table)
TableField.create('y', 'Y Value', table)

for (f1,f2) in [('w', 'x'), ('w', 'y'), ('x', 'y')]:
    ( TableField.create
      ('%s%s' % (f1, f2), '%s+%s Value' % (f1, f2), table,
       hidden = True, parent_keywords=[f1, f2],
       post_process_func = Function(funcs.postprocess_field_compute,
                                    params={'fields': [f1, f2]})))
    
Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table')
