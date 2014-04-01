# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import sys
import cgi
import json
import datetime
import importlib
import traceback
import logging

import pytz
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.template.defaultfilters import date
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.core import management
from django.utils.datastructures import SortedDict
from rest_framework import generics, views
from rest_framework.compat import View
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer

from rvbd.common.timeutils import round_time

from rvbd_portal.apps.datasource.models import Job, Table
from rvbd_portal.apps.datasource.serializers import TableSerializer
from rvbd_portal.apps.datasource.forms import TableFieldForm
from rvbd_portal.apps.devices.models import Device
from rvbd_portal.apps.report.models import Report, Section, Widget, WidgetJob
from rvbd_portal.apps.report.serializers import ReportSerializer
from rvbd_portal.apps.report.utils import create_debug_zipfile

logger = logging.getLogger(__name__)


def reload_config(request, namespace=None, report_slug=None):
    """ Reload all reports or one specific report
    """
    if namespace and report_slug:
        logger.debug("Reloading %s report" % report_slug)
        management.call_command('reload',
                                namespace=namespace,
                                report_name=report_slug)
    elif namespace:
        logger.debug("Reloading reports under namespace %s" % namespace)
        management.call_command('reload', namespace=namespace)
    else:
        logger.debug("Reloading all reports")
        management.call_command('reload')

    if ('HTTP_REFERER' in request.META and
        'reload' not in request.META['HTTP_REFERER']):
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    elif hasattr(request, 'QUERY_PARAMS') and 'next' in request.QUERY_PARAMS:
        return HttpResponseRedirect(request.QUERY_PARAMS['next'])
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


class ReportView(views.APIView):
    """ Main handler for /report/{id}
    """
    model = Report
    serializer_class = ReportSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

    def get(self, request, namespace=None, report_slug=None):
        # handle REST calls

        queryset = Report.objects.filter(enabled=True)

        if request.accepted_renderer.format != 'html':
            if namespace and report_slug:
                queryset = queryset.get(namespace=namespace,
                                        slug=report_slug)
            elif report_slug:
                queryset = queryset.get(namespace='default',
                                        slug=report_slug)
            elif namespace:
                queryset = queryset.filter(namespace='default')

            serializer = ReportSerializer(instance=queryset)
            return Response(serializer.data)

        # handle HTML calls
        try:
            if namespace is None:
                namespace = queryset[0].namespace

            if report_slug is None:
                qs = queryset.filter(namespace=namespace).order_by('position')
                kwargs = {'report_slug': qs[0].slug,
                          'namespace': namespace}
                return HttpResponseRedirect(reverse('report-view',
                                                    kwargs=kwargs))
            else:
                report = queryset.get(namespace=namespace, slug=report_slug)
        except:
            raise Http404

        logging.debug('Received request for report page: %s' % report_slug)

        # search across all enabled devices
        for device in Device.objects.all():
            if (device.enabled and ('host.or.ip' in device.host or
                                    device.username == '<username>' or
                                    device.password == '<password>' or
                                    device.password == '')):
                return HttpResponseRedirect('%s?invalid=true' %
                                            reverse('device-list'))

        profile = request.user.userprofile
        if not profile.profile_seen:
            # only redirect if first login
            return HttpResponseRedirect(reverse('preferences')+'?next=/report')

        # factory this to make it extensible
        form_init = {'ignore_cache': request.user.userprofile.ignore_cache}

        # Collect all fields organized by section, with section id 0
        # representing common report level fields
        fields_by_section = report.collect_fields_by_section()

        # Merge fields into a single dict for use by the Django Form # logic
        all_fields = SortedDict()
        [all_fields.update(c) for c in fields_by_section.values()]
        form = TableFieldForm(all_fields,
                              hidden_fields=report.hidden_fields,
                              initial=form_init)

        # Build a section map that indicates which section each field
        # belongs in when displayed
        section_map = []
        if fields_by_section[0]:
            section_map.append({'title': 'Common',
                                'parameters': fields_by_section[0]})

        for s in Section.objects.filter(report=report).order_by('position'):
            show = False
            for v in fields_by_section[s.id].values():
                if v.keyword not in (report.hidden_fields or []):
                    show = True
                    break

            if show:
                section_map.append({'title': s.title,
                                    'parameters': fields_by_section[s.id]})

        return render_to_response('report.html',
                                  {'report': report,
                                   'developer': profile.developer,
                                   'maps_version': profile.maps_version,
                                   'maps_api_key': profile.maps_api_key,
                                   'endtime': 'endtime' in form.fields,
                                   'form': form,
                                   'section_map': section_map,
                                   'show_sections': (len(section_map) > 1)},
                                  context_instance=RequestContext(request))

    def post(self, request, namespace=None, report_slug=None):
        # handle REST calls
        if namespace is None or report_slug is None:
            return self.http_method_not_allowed(request)

        logger.debug("Received POST for report %s, with params: %s" %
                     (report_slug, request.POST))

        try:
            report = Report.objects.get(namespace=namespace,
                                        slug=report_slug)
        except:
            raise Http404

        fields_by_section = report.collect_fields_by_section()
        all_fields = SortedDict()
        [all_fields.update(c) for c in fields_by_section.values()]
        form = TableFieldForm(all_fields, hidden_fields=report.hidden_fields,
                              data=request.POST, files=request.FILES)

        if form.is_valid():

            logger.debug('Form passed validation: %s' % form)
            formdata = form.cleaned_data
            logger.debug('Form cleaned data: %s' % formdata)

            # parse time and localize to user profile timezone
            profile = request.user.userprofile
            timezone = pytz.timezone(profile.timezone)
            form.apply_timezone(timezone)

            if formdata['debug']:
                logger.debug("Debugging report and rotating logs now ...")
                management.call_command('rotate_logs')

            logger.debug("Report %s validated form: %s" %
                         (report_slug, formdata))

            # setup definitions for each Widget
            definition = []

            # store datetime info about when report is being run
            # XXX move datetime format to preferences or somesuch
            now = datetime.datetime.now(timezone)
            definition.append({'datetime': str(date(now, 'jS F Y H:i:s')),
                               'timezone': str(timezone),
                               'debug': formdata['debug']})

            # create matrix of Widgets
            lastrow = -1
            rows = []
            for w in report.widgets().order_by('row', 'col'):
                if w.row != lastrow:
                    lastrow = w.row
                    rows.append([])
                rows[-1].append(Widget.objects.get_subclass(id=w.id))

            # populate definitions
            for row in rows:
                for w in row:
                    widget_def = {"widgettype": w.widgettype().split("."),
                                  "posturl": reverse('widget-job-list',
                                                     args=(report.namespace,
                                                           report.slug,
                                                           w.id)),
                                  "options": w.uioptions,
                                  "widgetid": w.id,
                                  "row": w.row,
                                  "width": w.width,
                                  "height": w.height,
                                  "criteria": w.criteria_from_form(form)
                                  }
                    definition.append(widget_def)

            logger.debug("Sending widget definitions for report %s: %s" %
                         (report_slug, definition))

            return HttpResponse(json.dumps(definition))
        else:
            # return form with errors attached in a HTTP 200 Error response
            return HttpResponse(str(form.errors), status=400)


class ReportCriteria(views.APIView):
    """ Handle requests for criteria fields.

        `get`  returns a json object of all criteria for the specified
               Report, or optionally for a specific widget within the Report

        `post` takes a criteria form and returns a json object of just
               the changed, or dynamic values
    """
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

    def get(self, request, namespace=None, report_slug=None, widget_id=None):
        try:
            all_fields = SortedDict()

            if widget_id:
                w = Widget.objects.get(pk=widget_id)
                all_fields = w.collect_fields()
            else:
                report = Report.objects.get(namespace=namespace,
                                            slug=report_slug)
                fields_by_section = report.collect_fields_by_section()
                for c in fields_by_section.values():
                    all_fields.update(c)
        except:
            raise Http404

        form = TableFieldForm(all_fields, use_widgets=False)

        # create object from the tablefield keywords
        # then populate it with the initial data that got generated by default
        keys = form._tablefields.keys()
        criteria = dict(zip(keys, [None]*len(keys)))
        criteria.update(form.data)

        return HttpResponse(json.dumps(criteria))

    def post(self, request, namespace=None, report_slug=None):
        # handle REST calls
        if report_slug is None:
            return self.http_method_not_allowed(request)

        logger.debug("Received POST for report %s, with params: %s" %
                     (report_slug, request.POST))

        try:
            report = Report.objects.get(slug=report_slug)
        except:
            raise Http404

        fields_by_section = report.collect_fields_by_section()
        all_fields = SortedDict()
        [all_fields.update(c) for c in fields_by_section.values()]

        form = TableFieldForm(all_fields, hidden_fields=report.hidden_fields,
                              data=request.POST, files=request.FILES)

        response = []

        for field in form.dynamic_fields():
            response.append({'id': field.auto_id,
                             'html': str(field)})
        return HttpResponse(json.dumps(response))


class ReportWidgets(views.APIView):
    """ Return default criteria values for all widgets, with latest time,
        if applicable.

        Used in auto-run reports when specifying detailed criteria isn't
        necessary.
    """

    def get(self, request, namespace=None, report_slug=None):
        try:
            report = Report.objects.get(namespace=namespace,
                                        slug=report_slug)
        except:
            raise Http404

        # parse time and localize to user profile timezone
        profile = request.user.userprofile
        timezone = pytz.timezone(profile.timezone)
        now = datetime.datetime.now(timezone)

        # pin the endtime to a round interval if we are set to
        # reload periodically
        minutes = report.reload_minutes
        if minutes:
            trimmed = round_time(dt=now, round_to=60*minutes, trim=True)
            if now - trimmed > datetime.timedelta(minutes=15):
                now = trimmed
            else:
                now = round_time(dt=now, round_to=60*report.reload_minutes)

        widget_defs = []

        widget_defs.append({'datetime': str(date(now, 'jS F Y H:i:s')),
                            'timezone': str(timezone),
                            })
        for w in report.widgets().order_by('row', 'col'):
            # get default criteria values for widget
            # and set endtime to now, if applicable
            criteria = ReportCriteria.as_view()(request,
                                                w.section.report.namespace,
                                                w.section.report.slug,
                                                w.id)
            widget_criteria = json.loads(criteria.content)
            if 'endtime' in widget_criteria:
                widget_criteria['endtime'] = now.isoformat()

            # setup json definition object
            widget_def = {
                "widgettype": w.widgettype().split("."),
                "posturl": reverse('widget-job-list',
                                   args=(w.section.report.namespace,
                                         w.section.report.slug,
                                         w.id)),
                "options": w.uioptions,
                "widgetid": w.id,
                "row": w.row,
                "width": w.width,
                "height": w.height,
                "criteria": widget_criteria
            }

            widget_defs.append(widget_def)

        return HttpResponse(json.dumps(widget_defs))


class ReportTableList(generics.ListAPIView):
    model = Table
    serializer_class = TableSerializer

    def get(self, request, *args, **kwargs):
        report = Report.objects.get(namespace=kwargs['namespace'],
                                    slug=kwargs['report_slug'])
        qs = (table
              for section in report.section_set.all()
              for widget in section.widget_set.all()
              for table in widget.tables.all())
        serializer = TableSerializer(instance=qs)
        return Response(serializer.data)


class WidgetJobsList(views.APIView):

    parser_classes = (JSONParser,)

    def post(self, request, namespace, report_slug, widget_id, format=None):
        logger.debug("Received POST for report %s, widget %s: %s" %
                     (report_slug, widget_id, request.POST))

        try:
            report = Report.objects.get(namespace=namespace, slug=report_slug)
            widget = Widget.objects.get(id=widget_id)
        except:
            raise Http404

        req_json = json.loads(request.POST['criteria'])

        fields = widget.collect_fields()

        form = TableFieldForm(fields, use_widgets=False,
                              hidden_fields=report.hidden_fields,
                              include_hidden=True,
                              data=req_json, files=request.FILES)

        if not form.is_valid():
            raise ValueError("Widget internal criteria form is invalid:\n%s" %
                             (form.errors.as_text()))

        if form.is_valid():
            logger.debug('Form passed validation: %s' % form)
            formdata = form.cleaned_data
            logger.debug('Form cleaned data: %s' % formdata)

            # parse time and localize to user profile timezone
            profile = request.user.userprofile
            timezone = pytz.timezone(profile.timezone)
            form.apply_timezone(timezone)

            form_criteria = form.criteria()
            logger.debug('Form_criteria: %s' % form_criteria)

            try:
                job = Job.create(table=widget.table(),
                                 criteria=form_criteria)
                job.start()

                wjob = WidgetJob(widget=widget, job=job)
                wjob.save()

                logger.debug("Created WidgetJob %s for report %s (handle %s)" %
                             (str(wjob), report_slug, job.handle))

                return Response({"joburl": reverse('report-job-detail',
                                                   args=[namespace,
                                                         report_slug,
                                                         widget_id,
                                                         wjob.id])})
            except Exception as e:
                logger.exception("Failed to start job, an exception occurred")
                return HttpResponse(str(e), status=400)

        else:
            logger.error("form is invalid, entering debugger")
            from IPython import embed; embed()


class WidgetJobDetail(views.APIView):

    def get(self, request, namespace, report_slug, widget_id, job_id, format=None):
        wjob = WidgetJob.objects.get(id=job_id)

        job = wjob.job
        widget = wjob.widget

        if not job.done():
            # job not yet done, return an empty data structure
            logger.debug("%s: Not done yet, %d%% complete" % (str(wjob),
                                                              job.progress))
            resp = job.json()
        elif job.status == Job.ERROR:
            resp = job.json()
            logger.debug("%s: Job in Error state, deleting Job" % str(wjob))
            wjob.delete()
        else:
            try:
                i = importlib.import_module(widget.module)
                widget_func = i.__dict__[widget.uiwidget].process
                if widget.rows > 0:
                    tabledata = job.values()[:widget.rows]
                else:
                    tabledata = job.values()

                if tabledata is None or len(tabledata) == 0:
                    resp = job.json()
                    resp['status'] = Job.ERROR
                    resp['message'] = "No data returned"
                    logger.debug("%s marked Error: No data returned" %
                                 str(wjob))
                elif (hasattr(i, 'authorized') and
                      not i.authorized(request.user.userprofile)[0]):
                    _, msg = i.authorized(request.user.userprofile)
                    resp = job.json()
                    resp['data'] = None
                    resp['status'] = Job.ERROR
                    resp['message'] = msg
                    logger.debug("%s Error: module unauthorized for user %s"
                                 % (str(wjob), request.user))
                else:
                    data = widget_func(widget, job, tabledata)
                    resp = job.json(data)
                    logger.debug("%s complete" % str(wjob))
            except:
                logger.exception("Widget %s Job %s processing failed" %
                                 (widget.id, job.id))
                resp = job.json()
                resp['status'] = Job.ERROR
                ei = sys.exc_info()
                resp['message'] = str(traceback.format_exception_only(ei[0],
                                                                      ei[1]))

            wjob.delete()

        resp['message'] = cgi.escape(resp['message'])

        return HttpResponse(json.dumps(resp))
