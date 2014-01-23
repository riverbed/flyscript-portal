from rvbd_portal.apps.report.models import Report, Section
import rvbd_portal.apps.report.modules.raw as raw
from rvbd_portal.apps.datasource.forms import fields_add_time_selection
from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import Column
from rvbd_portal.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Time Selection' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

table = AnalysisTable.create('test-criteria-timeselection', tables={}, 
                             func = funcs.analysis_echo_criteria)
fields_add_time_selection(table, initial_duration='1 day')

Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table')
