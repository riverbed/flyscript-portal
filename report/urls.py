from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, ListView
from report.models import Widget, Job

for j in Job.objects.all():
    j.delete()

urlpatterns = patterns(
    '',

    url(r'^(?P<report_id>[0-9]+)$', 'report.views.main'),
    url(r'^(?P<report_id>[0-9]+)/data/(?P<widget_id>[0-9]+)$', 'report.models.widgetdata'),
    )
