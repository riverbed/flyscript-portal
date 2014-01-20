from rvbd_common.apps.datasource.modules.analysis import AnalysisTable
from rvbd_common.apps.datasource.models import TableField, Column

from rvbd_common.apps.report.models import Report, Section
from rvbd_common.apps.report.modules import raw

from rvbd_common.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Parents', hidden_fields = ['report_computed',
                                                           'section_computed',
                                                           'table_computed'] )
report.save()

# Report-level independent
TableField.create(keyword='report_independent', label='Report Independent', obj=report)

# Report-level computed
TableField.create(keyword='report_computed', obj=report,
                  post_process_template='report_computed:{report_independent}',
                  hidden=False)

# Section 
section = Section(report=report, title='Section 0')
section.save()

# Section-level computed
TableField.create(keyword='section_computed', obj=section,
                  post_process_template='section_computed:{report_computed}',
                  hidden=False)

# Table
table = AnalysisTable.create('test-criteria-postprocess', tables={}, 
                             func = funcs.analysis_echo_criteria)

# Table-level computed
TableField.create(keyword='table_computed', obj=table,
                  post_process_template='table_computed:{section_computed}',
                  hidden=False)

Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table')
