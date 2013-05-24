# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import json
import datetime

import pytz
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext, loader
from django.template.defaultfilters import date
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


def reload_config(request, report_slug=None):
    """ Reload all reports or one specific report
    """
    if report_slug:
        report_id = Report.objects.get(slug=report_slug).id
    else:
        report_id = None
    management.call_command('reload', report_id=report_id)

    if 'HTTP_REFERER' in request.META and 'reload' not in request.META['HTTP_REFERER']:
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        return HttpResponseRedirect('/report')


class ReportView(APIView):

    #
    # Main handler for /report/{id}
    #
    def get(self, request, report_slug=None):
        try:
            if report_slug is None:
                reports = Report.objects.order_by('slug')
                return HttpResponseRedirect('/report/%s' % reports[0].slug)
            else:
                report = Report.objects.get(slug=report_slug)
        except:
            raise Http404

        timezone = 'UTC'
        timezone_changed = False
        if request.user.is_authenticated():
            profile = request.user.userprofile
            timezone = profile.timezone
            timezone_changed = profile.timezone_changed

        if timezone_changed:
            timezones = [timezone]
        else:
            timezones = pytz.common_timezones

        # check the first device in the report and verify it has been
        # setup appropriately
        widget = Widget.objects.filter(report=report)[0]
        table = widget.tables.all()[0]
        device = table.device
        if ('host.or.ip' in device.host or device.username == '<username>' or
                device.password == '<password>'):
            return HttpResponseRedirect('/data/devices')


        t = loader.get_template('report.html')
        c = RequestContext(request,
                           {'report': report,
                            'timezones': timezones,
                            'timezone_changed': timezone_changed,
                           });

        return HttpResponse(t.render(c))

    def put(self, request, report_slug):
        try:
            report = Report.objects.get(slug=report_slug)
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

        # store for future session reports
        # then create datetime object and convert to given timezone
        timezone = pytz.timezone(params['timezone'])
        request.session['django_timezone'] = timezone
        dt_naive = datetime.datetime.strptime(params['date'] + ' ' + params['time'],
                                              '%m/%d/%Y %I:%M%p')
        d = timezone.localize(dt_naive)

        # check for ignore_cache option
        ignore_cache = request.user.userprofile.ignore_cache or params['ignore_cache']

        definition = []

        # store datetime info about when report is being run
        # XXX move datetime format to preferences or somesuch
        now = datetime.datetime.now(timezone)

        definition.append({'datetime': str(date(now, 'jS F Y H:i:s')),
                           'timezone': str(timezone)})

        for row in rows:
            for w in row:
                widget_def = { "widgettype": w.widgettype().split("."),
                               "posturl": "/report/%s/widget/%d/jobs/" % (report.slug, w.id),
                               "options": json.loads(w.get_uioptions()),
                               "widgetid": w.id,
                               "row": w.row,
                               "width": w.width,
                               "height": w.height,
                               "criteria": {'endtime': datetime_to_seconds(d),
                                            'duration': params['duration'],
                                            'filterexpr': params['filterexpr'],
                                            'ignore_cache': ignore_cache}
                               }
                definition.append(widget_def)

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
        for w in Widget.objects.filter(report=report).order_by('row','col'):
            widget_forms.append((w.id, WidgetDetailForm(instance=w)))

        return render_to_response('configure.html',
                                  {'report': report,
                                   'reportForm': report_form,
                                   'widgetForms': widget_forms},
                                  context_instance=RequestContext(request))


class WidgetJobsList(APIView):

    parser_classes = (JSONParser,)

    def post(self, request, report_slug, widget_id, format=None):
        logger.debug("WidgetJobList(report %s, widget %s) POST: %s" %
                     (report_slug, widget_id, request.POST))

        criteria = json.loads(request.POST['criteria'])

        widget = Widget.objects.get(id=widget_id)

        if criteria['duration'] == 'Default':
            duration = None
        else:
            duration = parse_timedelta(criteria['duration']).total_seconds()
            
        job_criteria = Criteria(endtime=criteria['endtime'],
                            duration=duration,
                            filterexpr=criteria['filterexpr'])
        job = Job(table=widget.table(),
                  criteria=job_criteria.__dict__)
        job.save()
        job.start(ignore_cache=criteria['ignore_cache'])

        wjob = WidgetJob(widget=widget, job=job)
        wjob.save()

        logger.debug("Created WidgetJob %s: report %s, widget %s, job %s (handle %s)" %
                     (str(wjob), report_slug, widget_id, job.id, job.handle))
        
        return Response({"joburl": "/report/%s/widget/%s/jobs/%d/" % (report_slug, widget_id, wjob.id)})

class WidgetJobDetail(APIView):

    def get(self, request, report_slug, widget_id, job_id, format=None):
        wjob = WidgetJob.objects.get(id=job_id)
        return wjob.response()
        


