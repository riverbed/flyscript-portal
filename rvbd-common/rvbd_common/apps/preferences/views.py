# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import logging

from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response

from rvbd_common.apps.preferences.models import UserProfile
from rvbd_common.apps.preferences.forms import UserProfileForm

logger = logging.getLogger(__name__)


class PreferencesView(APIView):
    """ Display and update user preferences
    """
    renderer_classes = (TemplateHTMLRenderer, )

    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        if not profile.profile_seen:
            profile.profile_seen = True
            profile.save()
        form = UserProfileForm(instance=profile)
        return Response({'form': form}, template_name='preferences.html')

    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        form = UserProfileForm(request.DATA, instance=profile)
        if form.is_valid():
            form.save()
            profile = UserProfile.objects.get(user=request.user)
            if profile.timezone_changed:
                request.session['django_timezone'] = profile.timezone
                timezone.activate(profile.timezone)

            try:
                return HttpResponseRedirect(request.QUERY_PARAMS['next'])
            except KeyError:
                return HttpResponseRedirect(request.META['HTTP_REFERER'])
        else:
            return Response({'form': form}, template_name='preferences.html')


