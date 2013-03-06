from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView
from report.models import Job

for j in Job.objects.all():
    j.delete()

urlpatterns = patterns(
    '',

    url(r'^(?P<report_id>[0-9]+)$', 'report.views.main'),
    url(r'^(?P<report_id>[0-9]+)/data/(?P<datatable_id>[0-9]+)$', 'report.models.DataTable_poll'),
    url(r'^(?P<report_id>[0-9]+)/widget/(?P<widget_id>[0-9]+)$', 'report.models.Widget_poll'),
    )
