# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import json
import traceback
import datetime

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext, loader
from django.shortcuts import render_to_response
from django.core import management

from apps.datasource.models import Job, Criteria
from apps.report.models import Report, Widget, WidgetJob
from apps.report.forms import ReportDetailForm, WidgetDetailForm

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

from rvbd.common import datetime_to_seconds, parse_timedelta

import logging
logger = logging.getLogger(__name__)

def root(request):
    try:
        reports = Report.objects.all()
    except:
        return HttpResponse("No reports defined!")

    return HttpResponseRedirect('/report/%d' % reports[0].id)


def reload_config(request):
    from project import settings
    management.call_command('reload')

    # sets modified time on file so development server will restart
    #os.utime(os.path.join(settings.PROJECT_ROOT, 'project', 'urls.py'), None)

    if 'HTTP_REFERER' in request.META and 'reload' not in request.META['HTTP_REFERER']:
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        return HttpResponseRedirect('/report')


class ReportView(APIView):
    
    #
    # Main handler for /report/{id}
    #
    def get(self, request, report_id=None):
        try:
            reports = Report.objects.all()
            if report_id is None:
                report = reports[0]
            else:
                report = Report.objects.get(pk=int(report_id))
        except:
            raise Http404

        # check the first device in the report and verify it has been
        # setup appropriately
        widget = Widget.objects.filter(report=report.id)[0]
        table = widget.tables.all()[0]
        device = table.device
        if ('host.or.ip' in device.host or device.username == '<username>' or
                device.password == '<password>'):
            return HttpResponseRedirect('/data/devices')


        t = loader.get_template('report.html')
        c = RequestContext( request,
                            { 'report' : report,
                              'reports' : reports
                              } );

        return HttpResponse(t.render(c))

    def put(self, request, report_id):
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

        params = json.loads(request.raw_post_data)
        d = datetime.datetime.strptime(params['date'] + ' ' + params['time'], '%m/%d/%Y %I:%M%p')

        definition = []
        for row in rows:
            for w in row:
                widget_def = { "widgettype": w.widgettype().split("."),
                               "posturl": "/report/%d/widget/%d/jobs/" % (report.id, w.id),
                               "options": json.loads(w.get_uioptions()),
                               "widgetid": w.id,
                               "row": w.row,
                               "width": w.width,
                               "height": w.height,
                               "criteria" : { 'endtime': datetime_to_seconds(d),
                                              'duration': params['duration'],
                                              'filterexpr': params['filterexpr']}
                               }
                definition.append(widget_def)

        return HttpResponse(json.dumps(definition))

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

    def post(self, request, report_id, widget_id, format=None):
        logger.debug("WidgetJobList(report %s, widget %s) POST: %s" %
                     (report_id, widget_id, request.POST))

        criteria = json.loads(request.POST['criteria'])

        widget = Widget.objects.get(id=widget_id)

        if criteria['duration'] == 'Default':
            duration = None
        else:
            duration = parse_timedelta(criteria['duration']).total_seconds()
            
        criteria = Criteria(endtime=criteria['endtime'],
                            duration=duration,
                            filterexpr=criteria['filterexpr'])
        job = Job(table=widget.table(),
                  criteria=criteria.__dict__)
        job.save()
        job.start()

        wjob = WidgetJob(widget=widget, job=job)
        wjob.save()

        logger.debug("Created WidgetJob %s: report %s, widget %s, job %s (handle %s)" %
                     (str(wjob), report_id, widget_id, job.id, job.handle))
        
        return Response({"joburl": "/report/%s/widget/%s/jobs/%d/" % (report_id, widget_id, wjob.id)})
    
class WidgetJobDetail(APIView):

    def get(self, request, report_id, widget_id, job_id, format=None):
        wjob = WidgetJob.objects.get(id=job_id)
        return wjob.response()
        


