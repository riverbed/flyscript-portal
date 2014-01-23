# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin
from rvbd_portal.apps.devices.models import Device


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'host', 'port')

admin.site.register(Device, DeviceAdmin)
