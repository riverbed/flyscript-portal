# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django import forms

from rvbd_common.apps.preferences.models import UserProfile


class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

    class Meta:
        model = UserProfile
        exclude = ['user', 'timezone_changed', 'profile_seen']
        widgets = {'maps_version': forms.HiddenInput(),
                   'maps_api_key': forms.HiddenInput()}

    def clean(self):
        # check for API key if maps are either FREE or BUSINESS
        cleaned_data = super(UserProfileForm, self).clean()
        version = cleaned_data.get('maps_version')
        api_key = cleaned_data.get('maps_api_key')

        if not api_key and version in ('FREE', 'BUSINESS'):
            if version == 'FREE':
                msg = u'Usage of Free version of Google Maps requires API Key'
            else:
                msg = u'Usage of Business version of Google Maps requires API Key'
            self._errors['maps_api_key'] = self.error_class([msg])
            del cleaned_data['maps_api_key']

        return cleaned_data
