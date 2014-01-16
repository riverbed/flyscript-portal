# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#  https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin
from rvbd_common.apps.geolocation.models import Location


class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'mask', 'latitude', 'longitude')

admin.site.register(Location, LocationAdmin)
