from django import forms

from rvbd_common.apps.datasource.forms import fields_add_time_selection
from rvbd_common.apps.datasource.modules.analysis import AnalysisTable
from rvbd_common.apps.datasource.models import TableField, Table, Column
from rvbd_common.libs.fields import Function

from rvbd_common.apps.report.models import Report, Section
from rvbd_common.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Changing',
                field_order =['first', 'second'])
report.save()

section = Section(report=report, title='Section 0')
section.save()

TableField.create ('first', 'First Choice', section,
                   field_cls = forms.ChoiceField,
                   field_kwargs = {'choices': (('a', 'Option A'),
                                               ('b', 'Option B') ) })

TableField.create ('second', 'Second Choice', section,
                   field_cls = forms.ChoiceField,
                   pre_process_func =
                   Function(funcs.preprocess_changesecond),
                   dynamic=True)

table = AnalysisTable.create('test-criteria-changingchoices', tables={}, 
                             func = funcs.analysis_echo_criteria)
Column.create(table, 'key', 'Key', iskey=True, isnumeric=False)
Column.create(table, 'value', 'Value', isnumeric=False)

raw.TableWidget.create(section, table, 'Table')
