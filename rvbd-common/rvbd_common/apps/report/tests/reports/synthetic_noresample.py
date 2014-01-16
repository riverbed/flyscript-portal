from rvbd_common.apps.datasource.modules.analysis import AnalysisTable
from rvbd_common.apps.datasource.models import Column

from rvbd_common.apps.report.models import Report, Section
from rvbd_common.apps.report.modules import raw
from rvbd_common.apps.datasource.forms import fields_add_time_selection, fields_add_resolution

# Report
from rvbd_common.apps.report.tests.reports import synthetic_functions as funcs

report = Report(title='Synthetic No Resampling' )
report.save()

# Section 
section = Section(report=report, title='Section 0')
section.save()

# Table
table = AnalysisTable.create('test-synthetic-noresampling', tables={}, 
                             func = funcs.analysis_generate_data,
                             params = {'source_resolution': 60 })
fields_add_time_selection(table)
fields_add_resolution(table)

Column.create(table, 'time', 'Time', iskey=True, isnumeric=True, datatype='time')
Column.create(table, 'value', 'Value', isnumeric=True)

raw.TableWidget.create(section, table, 'Table')
