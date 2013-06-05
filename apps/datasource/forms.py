# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django import forms

from apps.datasource.models import Device


class DeviceDetailForm(forms.ModelForm):
    class Meta:
        model = Device

    def __init__(self, *args, **kwargs):
        # for existing model instances, change name and module fields
        # to read-only, to avoid user from editing those values easily
        super(DeviceDetailForm, self).__init__(*args, **kwargs)

        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['name'].widget.attrs['readonly'] = True
            self.fields['module'].widget.attrs['readonly'] = True
            self.fields['password'].widget.input_type = 'password'

    def clean_host(self):
        data = self.cleaned_data['host']
        if data.startswith('fill.in.'):
            raise forms.ValidationError('Please update with a valid hostname/ip address.')
        return data

    def clean_username(self):
        data = self.cleaned_data['username']
        if data == '<username>':
            raise forms.ValidationError('Please enter a valid username.')
        return data

    def clean_password(self):
        data = self.cleaned_data['password']
        if data == '<password>':
            raise forms.ValidationError('Please enter a valid password.')
        return data
