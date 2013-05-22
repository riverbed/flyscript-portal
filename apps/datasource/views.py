# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.http import HttpResponseRedirect
from django.forms.models import modelformset_factory

from rest_framework import generics
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.datasource.serializers import (DeviceSerializer, TableSerializer,
                                         ColumnSerializer, JobSerializer,
                                         JobListSerializer)
from apps.datasource.models import Device, Table, Column, Job
from apps.datasource.forms import DeviceDetailForm
from apps.datasource.devicemanager import DeviceManager


import logging
logger = logging.getLogger(__name__)

class TableList(generics.ListCreateAPIView):
    model = Table
    serializer_class = TableSerializer
    
class TableDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Table
    serializer_class = TableSerializer
    
class ColumnList(generics.ListCreateAPIView):
    model = Column
    serializer_class = ColumnSerializer
        
class ColumnDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Column
    serializer_class = ColumnSerializer
    
class JobList(generics.ListCreateAPIView):
    model = Job
    serializer_class = JobListSerializer

    def post_save(self, obj, created=False):
        obj.start()
    
class JobDetail(generics.RetrieveAPIView):
    model = Job
    serializer_class = JobSerializer


class DeviceList(generics.ListAPIView):
    model = Device
    serializer_class = DeviceSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)

    def get(self, request, *args, **kwargs):
        queryset = Device.objects.all()
        if request.accepted_renderer.format == 'html':
            DeviceFormSet = modelformset_factory(Device, form=DeviceDetailForm, extra=0)
            formset = DeviceFormSet()
            data = {'formset': formset}
            return Response(data, template_name='configure.html')

        serializer = DeviceSerializer(instance=queryset)
        data = serializer.data
        return Response(data)

    def put(self, request, *args, **kwargs):
        DeviceFormSet = modelformset_factory(Device, form=DeviceDetailForm, extra=0)
        formset = DeviceFormSet(request.DATA)

        if formset.is_valid():
            print 'valid formset'
            formset.save()
            DeviceManager.clear()
        else:
            data = {'formset': formset}
            return Response(data, template_name='configure.html')

        return HttpResponseRedirect(request.META['HTTP_REFERER'])


class DeviceDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Device
    serializer_class = DeviceSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
