# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


# Create your views here.
import os
import traceback

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext, loader
from django.shortcuts import render_to_response

from apps.report.models import Report, Widget
from apps.report.forms import ReportDetailForm, WidgetDetailForm

import logging
logger = logging.getLogger('report')

def root(request):
    try:
        reports = Report.objects.all()
    except:
        return HttpResponse("No reports defined!")

    return HttpResponseRedirect('/report/%d' % reports[0].id)

def main(request, report_id):
    try:
        report = Report.objects.get(pk=int(report_id))
    except:
        raise Http404

    reports = Report.objects.all()
    
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

    c = RequestContext( request,
                        { 'report' : report,
                          'reports' : reports,
                          'rows': rows} )
    
    return HttpResponse(t.render(c))


def poll(request, report_id, widget_id):
    try:
        ts = request.GET['ts']
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


