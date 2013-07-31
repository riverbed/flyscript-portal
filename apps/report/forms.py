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

import logging
logger = logging.getLogger(__name__)

DURATIONS = ('Default', '15 min', '1 hour', 
             '2 hours', '4 hours', '12 hours', '1 day')


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

    def __init__(self, *args, **kwargs):
        """ Handle arbitrary number of additional fields in `extra` keyword

            Keyword argument options:

            `extra` optional, a list of TableCriteria objects to append to
                    form listings

            `jsonform` optional, boolean indicating whether input and
                       validation will be handled via json input to 
                       toggle form fields appropriately (e.g. 
                       SplitDateTimeField becomes just IntegerField for
                       timestamp)
        """
        extra = kwargs.pop('extra')
        jsonform = False
        if 'jsonform' in kwargs:
            jsonform = kwargs.pop('jsonform')
        super(ReportCriteriaForm, self).__init__(*args, **kwargs)

        if extra:
            logging.debug('creating ReportCriteriaForm, with extra fields: %s' % extra)
            for i, field in enumerate(extra):
                field_id = 'criteria_%s' % field.id
                eval_field = '%s(label="%s")' % (field.field_type, field.label) 
                self.fields[field_id] = eval(eval_field)
                self.initial[field_id] = field.initial

        if jsonform:
            # toggle endtime formfield to handle timestamps via IntegerField
            self.fields['endtime'] = forms.IntegerField()

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


def create_report_criteria_form(*args, **kwargs):
    """ Factory function to create dynamic Report forms

        Included `report` kwargs will be assessed for
        any linked TableCriteria objects and passed to
        the initialization method for a ReportCriteriaForm.

        If the report has no associated TableCriteria, nothing
        special will occur, and a nominal form will be returned.
        
        Only objects which have no "parents" will be included,
        "parent" objects will later provide the form values
        to all children criteria during processing.
    """
    report = kwargs.pop('report')

    # use SortedDict to limit to unique criteria objects only
    extra = SortedDict()
    for c in report.criteria.all():
        if not c.parent:
            extra[c.id] = c
    for widget in Widget.objects.filter(report=report):
        for table in widget.tables.all():
            for tc in table.criteria.all():
                if not tc.parent:
                    extra[tc.id] = tc

    kwargs['extra'] = extra.values()
    return ReportCriteriaForm(*args, **kwargs)

