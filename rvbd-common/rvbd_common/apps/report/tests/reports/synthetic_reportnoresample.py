from rvbd_common.apps.datasource.modules.analysis import AnalysisTable
from rvbd_common.apps.datasource.models import Column

from rvbd_common.apps.report.models import Report, Section
from rvbd_common.apps.report.modules import raw
from rvbd_common.apps.datasource.forms import fields_add_time_selection, fields_add_resolution

from . import synthentic_functions as funcs

# Report
report = Report(title='Synthetic No Resampling' )
report.save()

# Section 
section = Section(report=report, title='Section 0')
section.save()

# Table
table = AnalysisTable.create('test-synthetic-noresampling', tables={}, 
                             func = funcs.analysis_echo_criteria)
fields_add_time_selection(table)
fields_add_resolution(table)

Column.create(table, 'time', 'Time', iskey=True, isnumeric=True, datatype='time')
Column.create(table, 'value', 'Value', isnumeric=True)

raw.TableWidget.create(section, table, 'Table')
