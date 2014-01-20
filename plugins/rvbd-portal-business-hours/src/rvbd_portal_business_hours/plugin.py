# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd_common.apps.plugins import Plugin


class BusinessHoursPlugin(Plugin):
    title = 'Business Hours Report Plugin'
    description = 'A business hours plugin with reports and support libraries',
    version = '0.0.1'

    enabled = True
    can_disable = True

    reports = ['reports.business_hours_report']
    libraries = ['libs']
