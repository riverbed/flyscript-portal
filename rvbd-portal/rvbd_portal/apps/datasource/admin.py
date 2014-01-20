# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from django.contrib import admin

from rvbd_portal.apps.datasource.models import Table, Column, Job


class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'module')
    list_filter = ('module', )

admin.site.register(Table, TableAdmin)


class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'table', 'iskey')
    list_filter = ('table', )

admin.site.register(Column, ColumnAdmin)


class JobAdmin(admin.ModelAdmin):
    list_display = ('table', 'status', 'progress', 'message')

admin.site.register(Job, JobAdmin)
