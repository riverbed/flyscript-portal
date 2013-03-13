# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView
from apps.report.models import Job

for j in Job.objects.all():
    j.delete()

urlpatterns = patterns(
    '',

    url(r'^(?P<report_id>[0-9]+)$', 'apps.report.views.main'),
    url(r'^(?P<report_id>[0-9]+)/widget/(?P<widget_id>[0-9]+)$', 'apps.report.views.poll'),
    )
