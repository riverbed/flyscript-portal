# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin

from rvbd_portal.apps.report.models import Report, Widget, WidgetJob


class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'enabled', 'position', 'sourcefile', 'slug')
    fieldsets = (
        (None, {
            'fields': ('title', 'position', 'enabled', 'slug',
                       'namespace', 'sourcefile', 'field_order',
                       'hidden_fields')
        }),
        ('Auto Reports', {
            'fields': ('hide_criteria', 'reload_minutes')
        }),
        ('Report Fields', {
            'classes': ('collapse',),
            'fields': ('fields',)
        })
    )
    filter_horizontal = ('fields',)
    actions = ['mark_enabled', 'mark_disabled']

    def mark_disabled(self, request, queryset):
        queryset.update(enabled=False)
    mark_disabled.short_description = 'Mark selected reports enabled'

    def mark_enabled(self, request, queryset):
        queryset.update(enabled=True)
    mark_enabled.short_description = 'Mark selected reports disabled'

admin.site.register(Report, ReportAdmin)


class WidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'module', 'uiwidget')
    list_filter = ('section', 'module', 'uiwidget', )

#admin.site.register(Widget, WidgetAdmin)


class WidgetJobAdmin(admin.ModelAdmin):
    pass

#admin.site.register(WidgetJob, WidgetJobAdmin)
