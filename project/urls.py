# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from django.conf.urls import patterns, include, url
from django.http import HttpResponseRedirect

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^favicon\.ico$', lambda x: HttpResponseRedirect('/static/images/favicon.ico')),
    url(r'^$', lambda x: HttpResponseRedirect('/report')),
    url(r'^report/', include('rvbd_portal.apps.report.urls')),
    url(r'^devices/', include('rvbd_portal.apps.devices.urls')),
    url(r'^data/', include('rvbd_portal.apps.datasource.urls')),
    url(r'^geolocation/', include('rvbd_portal.apps.geolocation.urls')),
    url(r'^help/', include('rvbd_portal.apps.help.urls')),
    url(r'^console/', include('rvbd_portal.apps.console.urls')),
    url(r'^preferences/', include('rvbd_portal.apps.preferences.urls')),
    url(r'^plugins/', include('rvbd_portal.apps.plugins.urls')),

    # third party packages
    url(r'^announcements/', include('announcements.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin_tools/', include('admin_tools.urls')),

    # Account login
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', 
        {'template_name': 'login.html'}),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout',
        {'next_page': '/accounts/login'}),
    url(r'^accounts/password_change/$', 'django.contrib.auth.views.password_change',
        {'post_change_redirect': '/preferences',
         'template_name': 'password_change_form.html'}),
)
