# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView
from apps.datasource.models import Job
from rest_framework.urlpatterns import format_suffix_patterns
from apps.datasource.views import TableList, TableDetail
from apps.datasource.views import ColumnList, ColumnDetail
from apps.datasource.views import JobList, JobDetail

# This happens on startup, flush all stale jobs
for j in Job.objects.all():
    j.delete()

urlpatterns = patterns(
    '',

    url(r'^tables/$',
        TableList.as_view(),
        name='table-list'),

    url(r'^tables/(?P<pk>[0-9]+)/$',
        TableDetail.as_view(),
        name='table-detail'),

    url(r'^columns/$',
        ColumnList.as_view(),
        name='column-list'),

    url(r'^columns/(?P<pk>[0-9]+)/$',
        ColumnDetail.as_view(),
        name='column-detail'),

    url(r'^jobs/$',
        JobList.as_view(),
        name='job-list'),
    
    url(r'^jobs/(?P<pk>[0-9]+)/$',
        JobDetail.as_view(),
        name='job-detail'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
