# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd_common.apps.plugins import Plugin, register


class WhoisReport(Plugin):
    title = 'Whois Report Plugin'
    description = 'Example Plugin providing report and helper script'
    version = '0.0.1'
    author = 'Riverbed Technology'

    enabled = True
    can_disable = True

    reports = ['reports.5_whois']
    libraries = ['libs']


register(WhoisReport)
