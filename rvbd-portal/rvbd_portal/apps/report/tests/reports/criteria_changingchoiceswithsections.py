from django import forms

from rvbd_portal.apps.datasource.forms import fields_add_time_selection
from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Table, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Changing with Sections',
                field_order =['first', 'second'])
report.save()

section = Section.create(report=report, title='Section 0', section_keywords=['first','second'])
section.save()

table = AnalysisTable.create('test-criteria-changingchoiceswithsections-0', tables={}, 
                             func = funcs.analysis_echo_criteria)
TableField.create ('first', 'First Choice', table,
                   field_cls = forms.ChoiceField,
                   field_kwargs = {'choices': (('a', 'Option A'),
                                               ('b', 'Option B') ) })

TableField.create ('second', 'Second Choice', table,
                   field_cls = forms.ChoiceField,
                   pre_process_func =
                   Function(funcs.preprocess_changesecond),
                   dynamic=True)

Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table 0')

section = Section.create(report=report, title='Section 1', section_keywords=['first','second'])
section.save()

table = AnalysisTable.create('test-criteria-changingchoiceswithsections-1', tables={}, 
                             func = funcs.analysis_echo_criteria)
TableField.create ('first', 'First Choice', table,
                   field_cls = forms.ChoiceField,
                   field_kwargs = {'choices': (('a', 'Option A'),
                                               ('b', 'Option B') ) })

TableField.create ('second', 'Second Choice', table,
                   field_cls = forms.ChoiceField,
                   pre_process_func =
                   Function(funcs.preprocess_changesecond),
                   dynamic=True)

Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table 1')
