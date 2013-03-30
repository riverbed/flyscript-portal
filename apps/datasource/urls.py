# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView
from apps.datasource.models import Job

# This happens on startup, flush all stale jobs
for j in Job.objects.all():
    j.delete()

urlpatterns = patterns(
    '',

    url(r'^(?P<table_id>[0-9]+)/poll$', 'apps.datasource.views.poll'),
    )
