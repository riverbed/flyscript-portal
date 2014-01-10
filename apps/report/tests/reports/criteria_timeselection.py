from apps.report.models import Report, Section
import apps.report.modules.raw as raw
from apps.datasource.forms import fields_add_time_selection
from apps.datasource.modules.analysis import AnalysisTable
from apps.datasource.models import Table, Column
from . import criteria_functions as funcs

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
