# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from rvbd_portal.apps.devices.views import DeviceList, DeviceDetail, DeviceDelete

urlpatterns = patterns(
    '',

    url(r'^$',
        DeviceList.as_view(),
        name='device-list'),

    url(r'^(?P<device_id>[0-9]+)/$',
        DeviceDetail.as_view(),
        name='device-detail'),

    # replace these with more REST-ful interfaces
    url(r'^(?P<device_id>[0-9]+)/delete$',
        DeviceDelete.as_view(),
        name='device-delete'),

    url(r'^add/$',
        DeviceDetail.as_view(),
        name='device-add'),

)

urlpatterns = format_suffix_patterns(urlpatterns)
