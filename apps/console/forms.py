# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django import forms

from apps.console.models import Utility, Results, Parameter, Job


class ExecuteForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ExecuteForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Utility
        exclude = ['parameters']


class UtilityDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UtilityDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Utility


class ParameterDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ParameterDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Parameter
