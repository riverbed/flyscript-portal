# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django.core.urlresolvers import reverse
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect
from rest_framework import generics
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.response import Response

from apps.devices.devicemanager import DeviceManager
from apps.devices.forms import DeviceDetailForm
from apps.devices.models import Device
from apps.devices.serializers import DeviceSerializer
from apps.preferences.models import UserProfile


class DeviceDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Device
    serializer_class = DeviceSerializer
    renderer_classes = (TemplateHTMLRenderer, JSONRenderer)


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
            formset.save()
            DeviceManager.clear()
            profile = UserProfile.objects.get(user=request.user)
            if not profile.profile_seen:
                # only redirect if first login
                return HttpResponseRedirect(reverse('preferences') + '?next=/report')
            elif '/devices' not in request.META['HTTP_REFERER']:
                return HttpResponseRedirect(request.META['HTTP_REFERER'])
            else:
                return HttpResponseRedirect(reverse('report-view-root'))

        else:
            data = {'formset': formset}
            return Response(data, template_name='configure.html')