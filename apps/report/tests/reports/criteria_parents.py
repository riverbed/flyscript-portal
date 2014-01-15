from django import forms

from apps.datasource.forms import fields_add_time_selection
from apps.datasource.modules.analysis import AnalysisTable
from apps.datasource.models import TableField, Table, Column
from libs.fields import Function

from apps.report.models import Report, Section
from apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Parents', hidden_fields = ['report_computed',
                                                           'section_computed',
                                                           'table_computed'] )
report.save()

# Report-level independent
report_parent = TableField.create(keyword='report_independent', label='Report Independent', obj=report)

# Report-level computed
report_computed = TableField.create(keyword='report_computed', obj=report,
                                    post_process_template='report_computed:{report_independent}',
                                    hidden=False)

# Section 
section = Section(report=report, title='Section 0')
section.save()

# Section-level computed
section_computed = TableField.create(keyword='section_computed', obj=section,
                                     post_process_template='section_computed:{report_computed}',
                                     hidden=False)

# Table
table = AnalysisTable.create('test-criteria-postprocess', tables={}, 
                             func = funcs.analysis_echo_criteria)

# Table-level computed
table_computed = TableField.create(keyword='table_computed', obj=table,
                                   post_process_template='table_computed:{section_computed}',
                                   hidden=False)

Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table')
