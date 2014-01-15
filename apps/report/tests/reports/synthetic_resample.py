from django import forms

from apps.datasource.forms import fields_add_time_selection
from apps.datasource.modules.analysis import AnalysisTable
from apps.datasource.models import TableField, Table, Column
from libs.fields import Function

from apps.report.models import Report, Section
from apps.report.modules import raw
from apps.datasource.forms import fields_add_time_selection, fields_add_resolution

from . import synthetic_functions as funcs

# Report
report = Report(title='Synthetic No Resampling' )
report.save()

# Section 
section = Section(report=report, title='Section 0')
section.save()

# Table
table = AnalysisTable.create('test-synthetic-resampling', tables={}, 
                             func = funcs.analysis_generate_data,
                             resample = True,
                             params = {'source_resolution': 60 })
fields_add_time_selection(table)
fields_add_resolution(table)

Column.create(table, 'time', 'Time', iskey=True, isnumeric=True, datatype='time')
Column.create(table, 'value', 'Value', isnumeric=True)

raw.TableWidget.create(section, table, 'Table')
