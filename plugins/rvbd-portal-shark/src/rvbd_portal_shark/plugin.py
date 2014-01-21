# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd_portal.apps.plugins import Plugin


class SharkPlugin(Plugin):
    title = 'Shark Datasource Plugin'
    description = 'A Portal datasource plugin with example report'
    version = '0.1'
    author = 'Riverbed Technology'

    enabled = True
    can_disable = True

    devices = ['devices']
    datasources = ['datasources']
    reports = ['reports']
