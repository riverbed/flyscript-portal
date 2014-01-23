# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django import forms
from django.forms.models import inlineformset_factory

from rvbd_portal.apps.console.models import Utility, Parameter


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
        exclude = ['islogfile']


class ParameterDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ParameterDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Parameter


class ParameterStringForm(forms.Form):
    parameter_string = forms.CharField(max_length=200,
                                       widget=forms.TextInput(attrs={'class': 'parameter-form'}),
                                       )


def get_utility_formset(extra=1):
    return inlineformset_factory(Utility,
                                 Parameter,
                                 form=ParameterDetailForm,
                                 extra=extra)
