# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import json
import datetime

import pytz
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext, loader
from django.template.defaultfilters import date
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.core import management

from apps.datasource.models import Job, Criteria
from apps.report.models import Report, Widget, WidgetJob
from apps.report.forms import ReportDetailForm, WidgetDetailForm
from apps.report.utils import create_debug_zipfile

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser

from rvbd.common import datetime_to_seconds, parse_timedelta

import logging
logger = logging.getLogger(__name__)


def reload_config(request, report_slug=None):
    """ Reload all reports or one specific report
    """
    if report_slug:
        report_id = Report.objects.get(slug=report_slug).id
        logger.debug("Reloading %s report" % report_slug)
    else:
        report_id = None
        logger.debug("Reloading all reports")

    management.call_command('reload', report_id=report_id)

    if ('HTTP_REFERER' in request.META and 
        'reload' not in request.META['HTTP_REFERER']):
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        return HttpResponseRedirect(reverse('report-view-root'))


def download_debug(request):
    """ Create zipfile and send it back to client
    """
    # XXX when we implement RBAC this method needs to be ADMIN-level only

    zipfile = create_debug_zipfile()
    wrapper = FileWrapper(file(zipfile))
    response = HttpResponse(wrapper, content_type='application/zip')
    zipname = os.path.basename(zipfile)
    response['Content-Disposition'] = 'attachment; filename=%s' % zipname
    response['Content-Length'] = os.stat(zipfile).st_size
    return response


class ReportView(APIView):
    """ Main handler for /report/{id}
    """

    def get(self, request, report_slug=None):
        try:
            if report_slug is None:
                reports = Report.objects.order_by('slug')
                return HttpResponseRedirect(reverse('report-view', 
                                                    args=[reports[0].slug]))
            else:
                report = Report.objects.get(slug=report_slug)
        except:
            raise Http404

        logging.debug('Received request for report page: %s' % report_slug)

        # check the devices in the report and verify all have been updated
        for widget in Widget.objects.filter(report=report):
            for table in widget.tables.all():
                device = table.device
                if device and (device.enabled and ('host.or.ip' in device.host or
                                                   device.username == '<username>' or
                                                   device.password == '<password>')):
                    return HttpResponseRedirect(reverse('device-list'))

        return render_to_response('report.html',
                                  {'report': report,
                                   'developer': request.user.userprofile.developer},
                                  context_instance=RequestContext(request))

    def post(self, request, report_slug):
        try:
            report = Report.objects.get(slug=report_slug)
        except:
            raise Http404

        params = request.POST 
        params['debug'] = (params['debug'] == 'true')
        
        if params['debug']:
            logger.debug("Debugging report and rotating logs now ...")
            management.call_command('rotate_logs')

        logger.debug("Received POST for report %s, with params: %s" %
                     (report_slug, params))

        # File upload debug
        if request.FILES:
            for n, f in request.FILES.iteritems():
                logger.debug("f %s: %s (%s)" % (str(f), f.name, f.size))

        # parse time and localize to user profile timezone
        profile = request.user.userprofile
        timezone = pytz.timezone(profile.timezone)
        dt_naive = datetime.datetime.strptime(params['date'] + ' ' + params['time'],
                                              '%m/%d/%Y %I:%M%p')
        local_time = timezone.localize(dt_naive)

        # setup definitions for each Widget
        definition = []

        # store datetime info about when report is being run
        # XXX move datetime format to preferences or somesuch
        now = datetime.datetime.now(timezone)
        definition.append({'datetime': str(date(now, 'jS F Y H:i:s')),
                           'timezone': str(timezone),
                           'debug': params['debug']})

        # create matrix of Widgets
        lastrow = -1
        rows = []
        for w in Widget.objects.filter(report=report).order_by('row', 'col'):
            if w.row != lastrow:
                lastrow = w.row
                rows.append([])
            rows[-1].append(Widget.objects.get_subclass(id=w.id))

        # populate definitions
        for row in rows:
            for w in row:
                widget_def = {"widgettype": w.widgettype().split("."),
                              "posturl": "/report/%s/widget/%d/jobs/" % (report.slug, w.id),
                              "options": w.uioptions,
                              "widgetid": w.id,
                              "row": w.row,
                              "width": w.width,
                              "height": w.height,
                              "criteria": {'endtime': datetime_to_seconds(local_time),
                                           'duration': params['duration'],
                                           'filterexpr': params['filterexpr'],
                                           'ignore_cache': 'ignore_cache' in params}
                              }
                definition.append(widget_def)

        logger.debug("Sending widget definitions for report %s: %s" %
                     (report_slug, definition))

        return HttpResponse(json.dumps(definition))
        

def configure(request, report_slug, widget_id=None):
    try:
        report = Report.objects.get(slug=report_slug)
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
        for w in Widget.objects.filter(report=report).order_by('row', 'col'):
            widget_forms.append((w.id, WidgetDetailForm(instance=w)))

        return render_to_response('configure.html',
                                  {'report': report,
                                   'reportForm': report_form,
                                   'widgetForms': widget_forms},
                                  context_instance=RequestContext(request))


class WidgetJobsList(APIView):

    parser_classes = (JSONParser,)

    def post(self, request, report_slug, widget_id, format=None):
        logger.debug("Received POST for report %s, widget %s: %s" %
                     (report_slug, widget_id, request.POST))

        req_criteria = json.loads(request.POST['criteria'])

        widget = Widget.objects.get(id=widget_id)

        if req_criteria['duration'] == 'Default':
            duration = None
        else:
            # py2.6 compatibility
            td = parse_timedelta(req_criteria['duration'])
            duration = float(td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
            
        job_criteria = Criteria(endtime=req_criteria['endtime'],
                                duration=duration,
                                filterexpr=req_criteria['filterexpr'],
                                table=widget.table(),
                                ignore_cache=req_criteria['ignore_cache'])
        job = Job(table=widget.table(),
                  criteria=job_criteria)
        job.save()
        job.start()

        wjob = WidgetJob(widget=widget, job=job)
        wjob.save()

        logger.debug("Created WidgetJob %s for report %s (handle %s)" %
                     (str(wjob), report_slug, job.handle))
        
        return Response({"joburl": reverse('report-job-detail',
                                           args=[report_slug, widget_id, wjob.id])})


class WidgetJobDetail(APIView):

    def get(self, request, report_slug, widget_id, job_id, format=None):
        wjob = WidgetJob.objects.get(id=job_id)
        return wjob.response()
