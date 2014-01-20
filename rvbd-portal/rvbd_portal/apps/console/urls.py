# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView

urlpatterns = patterns(
    'rvbd_portal.apps.console.views',
    url(r'^$', 'main'),
    url(r'^reload$', 'refresh'),
    url(r'(?P<script_id>[0-9]+)/detail$', 'detail'),
    url(r'(?P<script_id>[0-9]+)/run$', 'run'),
    url(r'(?P<script_id>[0-9]+)/status$', 'status'),
)
