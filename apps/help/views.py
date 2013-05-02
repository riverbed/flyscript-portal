# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import json
import operator

from django.http import HttpResponse, Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.generic.base import View

from apps.report.models import Report
from apps.datasource.models import Device
from apps.datasource.devicemanager import DeviceManager

from apps.help.forms import ProfilerInputForm

import logging
logger = logging.getLogger(__name__)


class ProfilerColumns(View):
    
    def get(self, request):
        try:
            reports = Report.objects.all()
        except:
            raise Http404

        form = ProfilerInputForm()

        return render_to_response('help.html',
                                  {'reports':reports, 'form': form},
                                  context_instance=RequestContext(request))

    def post(self, request):
        try:
            reports = Report.objects.all()
            device = Device.objects.filter(module='profiler')[0]
            profiler = DeviceManager.get_device(device.id)
        except:
            raise Http404

        form = ProfilerInputForm(request.POST)
        results = None
        if form.is_valid():
            data = form.cleaned_data
            results = profiler.search_columns(realms=[data['realm']],
                                              centricities=[data['centricity']],
                                              groupbys=[data['groupby']])
            results.sort(key=operator.attrgetter('key'))
            results.sort(key=operator.attrgetter('iskey'), reverse=True)

        return render_to_response('help.html',
                                  {'reports': reports,
                                   'form': form,
                                   'results': results},
                                  context_instance=RequestContext(request))

