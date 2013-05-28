# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import pytz
from django.http import Http404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone

from apps.preferences.models import UserProfile
from apps.preferences.forms import UserProfileForm

from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response


import logging
logger = logging.getLogger(__name__)


class PreferencesView(APIView):
    """ Display and update user preferences
    """
    renderer_classes = (TemplateHTMLRenderer, )

    @method_decorator(login_required)
    def get(self, request):
        profile = UserProfile.objects.get(user=request.user)
        form = UserProfileForm(instance=profile)
        return Response({'form': form}, template_name='preferences.html')

    @method_decorator(login_required)
    def post(self, request):
        profile = UserProfile.objects.get(user=request.user)
        form = UserProfileForm(request.DATA, instance=profile)
        if form.is_valid():
            form.save()
            profile = UserProfile.objects.get(user=request.user)
            if profile.timezone_changed:
                timezone.activate(profile.timezone)

            try:
                return HttpResponseRedirect(request.QUERY_PARAMS['next'])
            except KeyError:
                return HttpResponseRedirect(request.META['HTTP_REFERER'])
        else:
            return Response({'form': form}, template_name='preferences.html')


