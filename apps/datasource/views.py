# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.http import HttpResponseRedirect

from rest_framework import generics
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from apps.datasource.serializers import (DeviceSerializer, TableSerializer,
                                         ColumnSerializer, JobSerializer,
                                         JobListSerializer)
from apps.datasource.models import Device, Table, Column, Job
from apps.datasource.forms import DeviceDetailForm


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
            forms = [DeviceDetailForm(instance=q) for q in queryset]
            data = {'devices': queryset, 'forms': forms}
            return Response(data, template_name='configure.html')

        serializer = DeviceSerializer(instance=queryset)
        data = serializer.data
        return Response(data)

    def put(self, request, *args, **kwargs):

        device = Device.objects.get(pk=int(request.DATA['device_id']))
        form = DeviceDetailForm(request.DATA, instance=device)

        if form.is_valid():
            form.save()
        return HttpResponseRedirect(request.META['HTTP_REFERER'])


class DeviceDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Device
    serializer_class = DeviceSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)
