# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django import forms

from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.datasource.models import TableField

from rvbd_portal.apps.devices.models import Device
from rvbd_portal.apps.devices.devicemanager import DeviceManager


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device

    def __init__(self, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)

        self.fields['password'].widget.input_type = 'password'

    def clean(self):
        # field validation only really matters if the device was enabled
        cleaned_data = super(DeviceForm, self).clean()
        enabled = cleaned_data.get('enabled')

        if enabled:
            if cleaned_data.get('host', '').startswith('fill.in.'):
                msg = u'Please update with a valid hostname/ip address.'
                self._errors['host'] = self.error_class([msg])
                del cleaned_data['host']

            if cleaned_data.get('username', '') == '<username>':
                msg = u'Please enter a valid username.'
                self._errors['username'] = self.error_class([msg])
                del cleaned_data['username']

            if cleaned_data.get('password', '') == '<password>':
                msg = u'Please enter a valid password.'
                self._errors['password'] = self.error_class([msg])
                del cleaned_data['password']

        return cleaned_data


class DeviceListForm(forms.ModelForm):
    """ Used for displaying existing Devices in a list view
    """
    class Meta:
        model = Device
        fields = ('enabled', )


class DeviceDetailForm(DeviceForm):
    """ Used for creating new Devices, or editing existing ones
    """
    def __init__(self, *args, **kwargs):
        super(DeviceDetailForm, self).__init__(*args, **kwargs)

        modules = DeviceManager.list_modules()
        choices = zip(modules, modules)

        self.fields['module'] = forms.ChoiceField(choices=choices)

def fields_add_device_selection(obj, keyword='device',
                                label='Device',
                                module=None, enabled=None):
    field = TableField(keyword=keyword, label=label,
                       field_cls = forms.ChoiceField,
                       pre_process_func = Function(device_selection_preprocess,
                                                  {'module': module,
                                                   'enabled': enabled}))
    field.save()
    obj.fields.add(field)

def device_selection_preprocess(form, field, field_kwargs, params):
    filter_ = {}
    for k in ['module', 'enabled']:
        if k in params and params[k] is not None:
            filter_[k] = params[k]

    devices = Device.objects.filter(**filter_)
    if len(devices) == 0:
        choices = [('', '<No devices available>')]
    else:
        choices = [(d.id, d.name) for d in devices]

    field_kwargs['choices'] = choices
