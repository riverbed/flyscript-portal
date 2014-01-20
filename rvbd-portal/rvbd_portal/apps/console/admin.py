# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin

from rvbd_portal.apps.console.models import Utility, Results, Parameter, ConsoleJob


class UtilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'path', 'islogfile')

admin.site.register(Utility, UtilityAdmin)


class ResultsAdmin(admin.ModelAdmin):
    pass

admin.site.register(Results, ResultsAdmin)


class ParameterAdmin(admin.ModelAdmin):
    pass

admin.site.register(Parameter, ParameterAdmin)


class ConsoleJobAdmin(admin.ModelAdmin):
    pass

admin.site.register(ConsoleJob, ConsoleJobAdmin)
