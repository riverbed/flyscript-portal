# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin

from rvbd_common.apps.report.models import Report, Widget, WidgetJob


class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'position', 'sourcefile', 'slug')

admin.site.register(Report, ReportAdmin)


class WidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'module', 'uiwidget')
    list_filter = ('section', 'module', 'uiwidget', )

admin.site.register(Widget, WidgetAdmin)


class WidgetJobAdmin(admin.ModelAdmin):
    pass

admin.site.register(WidgetJob, WidgetJobAdmin)
