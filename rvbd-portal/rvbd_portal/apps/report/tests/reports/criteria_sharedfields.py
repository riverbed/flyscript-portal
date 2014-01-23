from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from rvbd_portal.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Shared Fields' )
report.save()

section = Section(report=report, title='Section')
section.save()

x = TableField.create('x', 'X Value')
for i in range(2):

    table = AnalysisTable.create('test-criteria-sharedfields-%d' % i, tables={}, 
                                 func = funcs.analysis_echo_criteria)
    Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
    Column.create(table, 'value', 'Value', isnumeric=False)

    table.fields.add(x)
    y = TableField.create('y', 'Y Value', table,
                          hidden=True,
                          parent_keywords = ['x'],
                          post_process_func = Function(funcs.sharedfields_compute,
                                                       params={'factor': 10*(i+1)}))


    
    raw.TableWidget.create(section, table, 'Table %d' % i)
