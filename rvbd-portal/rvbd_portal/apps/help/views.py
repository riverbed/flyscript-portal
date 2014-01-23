# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import operator
import logging

from django.http import Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.views.generic.base import View

from rvbd_portal.apps.devices.devicemanager import DeviceManager
from rvbd_portal.apps.help.forms import ProfilerInputForm, SharkInputForm
logger = logging.getLogger(__name__)


class ColumnHelper(View):
    
    def get(self, request, device_type):
        if device_type == 'profiler':
            form = ProfilerInputForm()
        elif device_type == 'shark':
            form = SharkInputForm()
        else:
            raise Http404

        return render_to_response('help.html',
                                  {'device': device_type.title(), 'form': form},
                                  context_instance=RequestContext(request))

    def post(self, request, device_type):
        if device_type == 'profiler':
            form = ProfilerInputForm(request.POST)
        elif device_type == 'shark':
            form = SharkInputForm(request.POST)
        else:
            raise Http404

        results = None
        if form.is_valid():
            data = form.cleaned_data
            if device_type == 'profiler':
                profiler = DeviceManager.get_device(data['device'])

                results = profiler.search_columns(realms=[data['realm']],
                                                  centricities=[data['centricity']],
                                                  groupbys=[data['groupby']])
                results.sort(key=operator.attrgetter('key'))
                results.sort(key=operator.attrgetter('iskey'), reverse=True)
                results = [(c.iskey, c.key, c.label, c.id) for c in results]
            elif device_type == 'shark':
                shark = DeviceManager.get_device(data['device'])

                results = [(f.id, f.description, f.type) for f in shark.get_extractor_fields()]
                results.sort(key=operator.itemgetter(0))

        return render_to_response('help.html',
                                  {'device': device_type.title(),
                                   'form': form,
                                   'results': results},
                                  context_instance=RequestContext(request))

