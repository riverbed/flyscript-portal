# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import json
import traceback

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext, loader
from django.shortcuts import render_to_response

from apps.datasource.models import Job
from apps.report.models import Report, Widget, WidgetJob
from apps.report.forms import ReportDetailForm, WidgetDetailForm

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

import logging
logger = logging.getLogger(__name__)

def root(request):
    try:
        reports = Report.objects.all()
    except:
        return HttpResponse("No reports defined!")

    return HttpResponseRedirect('/report/%d' % reports[0].id)

#
# Main handler for /report/{id}
#
def main(request, report_id=None):
    try:
        reports = Report.objects.all()
        if report_id is None:
            report = reports[0]
        else:
            report = Report.objects.get(pk=int(report_id))
    except:
        raise Http404

    t = loader.get_template('report.html')

    lastrow = -1
    i = -1
    rows = []
    for w in Widget.objects.filter(report=report).order_by('row','col'):
        if w.row != lastrow:
            i = i+1
            lastrow = w.row
            rows.append([])
        rows[i].append(Widget.objects.get_subclass(id=w.id))

    try:
        ts = request.POST['ts']
    except:
        ts = 1

    print "TIME: %s" % ts
        
    c = RequestContext( request,
                        { 'report' : report,
                          'reports' : reports,
                          'rows': rows,
                          'ts': ts
                          } )
    
    return HttpResponse(t.render(c))

def report_structure(request, report_id):
    try:
        report = Report.objects.get(pk=int(report_id))
    except:
        raise Http404

    lastrow = -1
    i = -1
    rows = []
    for w in Widget.objects.filter(report=report).order_by('row','col'):
        if w.row != lastrow:
            i = i+1
            lastrow = w.row
            rows.append([])
        rows[i].append(Widget.objects.get_subclass(id=w.id))

    if 'ts' in request.GET:
        ts = request.GET['ts']
    elif 'ts' in request.POST:
        ts = request.POST['ts']
    else:
        ts = 1

    definition = []
    for row in rows:
        for w in row:
            widget_def = { "widgettype": w.widgettype().split("."),
                           "posturl": "/report/%d/widget/%d/jobs/" % (report.id, w.id),
                           "options": json.loads(w.get_uioptions()),
                           "widgetid": w.id,
                           "row": w.row,
                           "colwidth": w.colwidth,
                           "ts" : ts }
            definition.append(widget_def)

    return HttpResponse(json.dumps(definition))

def poll(request, report_id, widget_id):
    try:
        if 'ts' in request.GET:
            ts = request.GET['ts']
        elif 'ts' in request.POST:
            ts = request.POST['ts']
        else:
            ts = 1
        widget = Widget.objects.get(id=widget_id)
        return widget.poll(ts)
    except:
        traceback.print_exc()
        return HttpResponse("Internal Error")

def configure(request, report_id, widget_id=None):
    try:
        reports = Report.objects.all()
        report = Report.objects.get(pk=int(report_id))
        if widget_id:
            widget = Widget.objects.get(pk=widget_id)
    except:
        raise Http404

    if request.method == 'POST':
        if widget_id is None:
            # updating report name
            form = ReportDetailForm(request.POST, instance=report)
            if form.is_valid():
                form.save()
        else:
            form = WidgetDetailForm(request.POST, instance=widget)
            if form.is_valid():
                form.save()
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        report_form = ReportDetailForm(instance=report)

        widget_forms = []
        for w in Widget.objects.filter(report=report).order_by('row','col'):
            widget_forms.append((w.id, WidgetDetailForm(instance=w)))

        return render_to_response('configure.html',
                                  {'reports': reports,
                                   'report': report,
                                   'reportForm': report_form,
                                   'widgetForms': widget_forms},
                                  context_instance=RequestContext(request))

class WidgetJobsList(APIView):

    parser_classes = (JSONParser,)

    def get(self, request, format=None):
        print "WidgetJobList get: %s" % request.DATA
        return Response({"status": 3, "message": "test error"})

    def post(self, request, report_id, widget_id, format=None):
        print "WidgetJobs post: %s" % request.DATA
        widget = Widget.objects.get(id=widget_id)
        job = Job(table=widget.table())
        job.save()
        job.start()

        wjob = WidgetJob(widget=widget, job=job)
        wjob.save()
        
        return Response({"joburl": "/report/%s/widget/%s/jobs/%d/" % (report_id, widget_id, wjob.id)})
    
class WidgetJobDetail(APIView):

    def get(self, request, report_id, widget_id, job_id, format=None):
        print "WidgetJobDetail (%s) get: %s" % (job_id, request.DATA)
        wjob = WidgetJob.objects.get(id=job_id)
        return wjob.response()
        


