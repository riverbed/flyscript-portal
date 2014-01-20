# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from django.conf.urls import patterns, url
import rvbd_portal.apps.report.views as views

urlpatterns = patterns(
    'rvbd_portal.apps.report.views',
    url(r'^$', views.ReportView.as_view(),
        name='report-view-root'),

    url(r'^reload$', 'reload_config',
        name='reload-all'),

    url(r'^(?P<report_slug>[0-9_a-zA-Z]+)/$',
        views.ReportView.as_view(),
        name='report-view'),

    url(r'^(?P<report_slug>[0-9_a-zA-Z]+)/criteria/$',
        views.ReportCriteriaChanged.as_view(),
        name='report-criteria-changed'),

    url(r'^(?P<report_slug>[0-9_a-zA-Z]+)/tables/$',
        views.ReportTableList.as_view(),
        name='report-table-list'),

    url(r'^(?P<report_slug>[0-9_a-zA-Z]+)/reload$',
        'reload_config',
        name='reload-report'),

    url(r'^(?P<report_slug>[0-9_a-zA-Z]+)/widget/(?P<widget_id>[0-9]+)/jobs/$',
        views.WidgetJobsList.as_view(),
        name='widget-job-list'),
    
    url(r'^(?P<report_slug>[0-9_a-zA-Z]+)/widget/(?P<widget_id>[0-9]+)/jobs/(?P<job_id>[0-9]+)/$',
        views.WidgetJobDetail.as_view(),
        name='report-job-detail'),

    # this makes more sense at the project level, but since its implemented 
    # under `report`, lets have the url here for now
    url(r'^download_debug$', 'download_debug'),
)
