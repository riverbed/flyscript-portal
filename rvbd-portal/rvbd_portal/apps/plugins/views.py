# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import json

from django.http import Http404, HttpResponse
from django.contrib import messages
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response

from rvbd_portal.apps.plugins import plugins

import logging
logger = logging.getLogger(__name__)


class PluginsListView(APIView):
    """ Display list of installed plugins """

    renderer_classes = (TemplateHTMLRenderer, )

    def get(self, request):
        changed = request.QUERY_PARAMS.get('changed', False)

        return Response({'plugins': list(plugins.all()),
                         'changed': changed},
                        template_name='plugins_list.html')


class PluginsDetailView(APIView):
    """ Display detail of specific plugin """

    renderer_classes = (TemplateHTMLRenderer, )

    def get(self, request, slug, *args, **kwargs):
        try:
            plugin = plugins.get(slug)
        except KeyError:
            return Http404

        return Response({'plugin': plugin})

    def post(self, request, slug, *args, **kwargs):
        """ Enable or disable plugin - rest of details are read-only """
        try:
            plugin = plugins.get(slug)
        except KeyError:
            return Http404

        enabled = request.DATA.get('enabled', False)

        # since we don't have helpful form cleaning, check for json 'false' too
        if (enabled == 'false' or enabled is False) and plugin.can_disable:
            plugin.enabled = False
            msg = 'Plugin %s disabled.' % plugin.title
        else:
            plugin.enabled = True
            msg = 'Plugin %s enabled.' % plugin.title

        messages.add_message(request, messages.INFO, msg)

        return HttpResponse(json.dumps({'plugin': plugin.__dict__}))
