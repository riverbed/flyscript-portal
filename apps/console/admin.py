# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin

from apps.console.models import Utility, Results, Parameter, Job


class UtilityAdmin(admin.ModelAdmin):
    pass
admin.site.register(Utility, UtilityAdmin)


class ResultsAdmin(admin.ModelAdmin):
    pass
admin.site.register(Results, ResultsAdmin)


class ParameterAdmin(admin.ModelAdmin):
    pass
admin.site.register(Parameter, ParameterAdmin)


class JobAdmin(admin.ModelAdmin):
    pass
admin.site.register(Job, JobAdmin)
