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
    url(r'^$', lambda x: HttpResponseRedirect('/report')),
    url(r'^report/', include('apps.report.urls')),
    url(r'^data/', include('apps.datasource.urls')),
    url(r'^geolocation/', include('apps.geolocation.urls')),
    url(r'^help/', include('apps.help.urls')),
    url(r'^console/', include('apps.console.urls')),

    # Examples:
    # url(r'^$', 'flybox.views.home', name='home'),
    # url(r'^flybox/', include('flybox.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
