# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.conf.urls import patterns, include, url
from rest_framework.urlpatterns import format_suffix_patterns

# This happens on startup, flush all stale jobs
from apps.devices.views import DeviceList

urlpatterns = patterns(
    '',

    url(r'^$',
        DeviceList.as_view(),
        name='device-list'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
