# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


from django import forms

from rvbd_common.apps.report.models import Report, Widget

import logging
logger = logging.getLogger(__name__)

DURATIONS = ('Default', '15 min', '1 hour', 
             '2 hours', '4 hours', '12 hours', '1 day',
             '1 week', '4 weeks')


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

