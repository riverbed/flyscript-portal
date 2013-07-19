# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django import forms
from django.forms import widgets
from django.utils.datastructures import SortedDict
from django.utils.html import format_html

from rvbd.common import datetime_to_seconds

from apps.report.models import Report, Widget
from apps.datasource.models import Criteria

DURATIONS = ('Default', '15 min', '1 hour', '2 hours', '4 hours', '12 hours', '1 day')


class ReportDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReportDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Report


class WidgetDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(WidgetDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Widget
        exclude = ['tables', 'module', 'uiwidget', 'uioptions']


class ReportDateWidget(forms.DateInput):
    """ Custom DateWidget for Reports
    """

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'date'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(ReportDateWidget, self).__init__(attrs=final_attrs, format=format)

    def render(self, *args, **kwargs):
        msg = '{0} <span id="datenow" class="icon-calendar" title="Set date to today"> </span> '
        return msg.format(super(ReportDateWidget, self).render(*args, **kwargs))


class ReportTimeWidget(forms.TimeInput):
    """ Custom TimeWidget for Reports
    """

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'time'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(ReportTimeWidget, self).__init__(attrs=final_attrs, format=format)

    def render(self, *args, **kwargs):
        msg = '{0} <span id="timenow" class="icon-time" title="Set time/date to now"> </span> '
        return msg.format(super(ReportTimeWidget, self).render(*args, **kwargs))


class ReportSplitDateTimeWidget(forms.SplitDateTimeWidget):
    """ A SplitDateTime Widget that uses overridden Report widgets
    """
    def __init__(self, attrs=None):
        split_widgets = [ReportDateWidget, ReportTimeWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, split_widgets, attrs)


class ReportCriteriaForm(forms.Form):
    """ Base Form for Report Criteria
    """
    # css definitions
    error_css_class = 'text-error'

    # field definitions
    endtime = forms.SplitDateTimeField(label='Report End Time',
                                       input_time_formats=['%I:%M %p'], 
                                       input_date_formats=['%m/%d/%Y'], 
                                       widget=ReportSplitDateTimeWidget)
    duration = forms.ChoiceField(choices=zip(DURATIONS, DURATIONS),
                                 widget=forms.Select(attrs={'class': 'duration'}))
    filterexpr = forms.CharField(label='Filter Expression',
                                 required=False, max_length=100,
                                 widget=forms.TextInput(attrs={'class': 'filterexpr'}))
    ignore_cache = forms.BooleanField(required=False, widget=forms.HiddenInput)
    debug = forms.BooleanField(required=False, widget=forms.HiddenInput)

    def criteria(self):
        """ Return certain field values as a dict for simple json parsing
        """
        result = {}
        for k, v in self.cleaned_data.iteritems():
            if k == 'endtime':
                result[k] = datetime_to_seconds(v)
            elif k != 'debug':
                result[k] = v
        return result




#
### XXX Placeholder class and factory functions - not used yet
class TableCriteriaForm(ReportCriteriaForm):
    """ Adds additional fields to Report Criteria Form
    """
    pass


def criteria_form_factory(base_form=None, extra_fields=None):
    """ Return a CriteriaForm class with fields for each of the 
        baseline keys (except hidden keys) and any extra fields as 
        requested

        `base_form` - new class will extend fields defined in this base class
        `extra_fields` - list of (field_name, form_field_class) tuples
    """
    fields = SortedDict()

    # create new objects based on base_forms field classes
    if base_form:
        for k, v in base_form.fields:
            fields[k] = v.__class__()

    if extra_fields:
        for field_name, field_class in extra_fields:
            fields[field_name] = field_class()

    return type('CriteriaForm', (forms.BaseForm,), {'base_fields': fields})


def report_criteria_form_factory(extra_fields=None):
    """ Return CriteriaForm with default set of report criteria
    """
    # start with base set of fields
    fields = [('endtime', forms.TimeField),
              ('duration', forms.CharField(max_length=10)),
              ('filterexpr', forms.CharField(max_length=100)),
              ('ignore_cache', forms.BooleanField())]
    return criteria_form_factory(base_form=None, extra_fields=fields)


def table_criteria_form_factory(fieldlist=None):
    """ Using list of tuples in fieldset, create a form for TableCriteria
    """
    if fieldlist is None:
        # XXX do we raise error instead?
        return

    return type('TableCriteriaForm', (forms.BaseForm,), {'base_fields': fieldlist})


