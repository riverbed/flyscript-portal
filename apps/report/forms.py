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

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'date'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(ReportDateWidget, self).__init__(attrs=final_attrs, format=format)


class ReportTimeWidget(forms.TimeInput):

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'time'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(ReportTimeWidget, self).__init__(attrs=final_attrs, format=format)


class ReportSplitDateTimeWidget(forms.SplitDateTimeWidget):
    """
    A SplitDateTime Widget that has some admin-specific styling.
    """
    def __init__(self, attrs=None):
        split_widgets = [ReportDateWidget, ReportTimeWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, split_widgets, attrs)

    def format_output(self, rendered_widgets):
        return format_html('<p class="datetime">'
                           '{0} {1} <span id="datenow" class="icon-calendar" title="Set date to today"> </span><br />'
                           '{2} {3} <span id="timenow" class="icon-time" title="Set time/date to now"> </span></p>',
                           'Date:', rendered_widgets[0], 
                           'Time:', rendered_widgets[1])


class ReportCriteriaForm(forms.Form):
    """ Base Form for Report Criteria
    """
    # css definitions
    error_css_class = 'text-error'

    # field definitions
    endtime = forms.SplitDateTimeField(input_time_formats=['%I:%M %p'], 
                                       input_date_formats=['%m/%d/%Y'], 
                                       widget=ReportSplitDateTimeWidget)
    duration = forms.ChoiceField(choices=zip(DURATIONS, DURATIONS),
                                 widget=forms.Select(attrs={'class': 'duration'}))
    filterexpr = forms.CharField(required=False, max_length=100,
                                 widget=forms.TextInput(attrs={'class': 'filterexpr'}))
    ignore_cache = forms.BooleanField(required=False, widget=forms.HiddenInput)
    debug = forms.BooleanField(required=False, widget=forms.HiddenInput)


### XXX Placeholder factory functions - not used yet
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
