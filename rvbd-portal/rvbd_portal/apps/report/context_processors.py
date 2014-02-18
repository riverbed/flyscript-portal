# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd_portal.apps.report.models import Report


def report_list_processor(request):
    return {'reports': Report.objects.filter(enabled=True).order_by('position')}
