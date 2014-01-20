# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from rvbd_portal.apps.datasource.views import TableList, TableDetail
from rvbd_portal.apps.datasource.views import TableColumnList, TableJobList
from rvbd_portal.apps.datasource.views import ColumnList, ColumnDetail
from rvbd_portal.apps.datasource.views import JobList, JobDetail, JobDetailData


urlpatterns = patterns(
    '',

    url(r'^tables/$',
        TableList.as_view(),
        name='table-list'),

    url(r'^tables/(?P<pk>[0-9]+)/$',
        TableDetail.as_view(),
        name='table-detail'),

    url(r'^tables/(?P<pk>[0-9]+)/columns/$',
        TableColumnList.as_view(),
        name='table-column-list'),

    url(r'^tables/(?P<pk>[0-9]+)/jobs/$',
        TableJobList.as_view(),
        name='table-job-list'),

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

    url(r'^jobs/(?P<pk>[0-9]+)/data/$',
        JobDetailData.as_view(),
        name='job-detail-data'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
