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

fields_add_time_selection(section, initial_duration='1 day')

table = AnalysisTable.create('test-criteria-timeselection', tables={}, duration=60,
                             func = funcs.criteria)
Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table')
