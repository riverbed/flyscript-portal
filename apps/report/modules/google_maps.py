# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import pygeoip
from pygeoip.util import ip2long
import socket
import json
import socket
import threading
import os.path

from apps.report.models import *
from apps.geolocation.models import Location
from apps.geolocation.geoip import Lookup
from rvbd.common.utils import DictObject

class MapWidget:
    @classmethod
    def create(cls, report, table, title, width=6, height=300):
        w = Widget(report=report, title=title, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey == True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))

        valuecols = [col.name for col in table.get_columns() if col.iskey == False]
        if len(valuecols) == 0:
            raise ValueError("Table %s does not have any value columns defined" % str(table))

            
        w.options = { 'key' : keycols[0],
                      'value': valuecols[0] }
        w.save()
        w.tables.add(table)
        
    
    @classmethod
    def process(cls, widget, data):
        columns = widget.table().get_columns()

        catcol = [c for c in columns if c.name == widget.get_option('key')][0]
        col = [c for c in columns if c.name == widget.get_option('value')][0]

        circles = []
        if data:
            valmin = data[0][1]
            valmax = valmin

            for reportrow in data:
                val = reportrow[1]
                valmin = min(val, valmin)
                valmax = max(val, valmax)

            geolookup = None
            print "geolookup: %s" % geolookup


            if col.datatype == 'bytes':
                formatter = 'formatBytes'
            elif wc.datatype == 'metric':
                formatter = 'formatMetric'
            else:
                formatter = None;

            for reportrow in data:
                key = reportrow[0]
                val = reportrow[1]

                if widget.table().options['groupby'] == 'host_group':
                    geo = Location.objects.get(name=key)
                else:
                    if geolookup == None:
                        geolookup = Lookup.instance()
                    geo = geolookup.lookup(key)

                if geo:
                    print "geo: %s" % geo
                    circle = {
                        'strokeColor': '#FF0000',
                        'strokeOpacity': 0.8,
                        'strokeWeight': 2,
                        'fillColor': '#FF0000',
                        'fillOpacity': 0.35,
                        'center': [geo.latitude, geo.longitude],
                        'size': 15*(val / valmax),
                        'title': geo.name,
                        'value': val,
                        'units': col.units,
                        'formatter': formatter
                        };

                    circles.append(circle)
        else:
            # no data just return empty circles list
            pass

        data = {
            "chartTitle": widget.title,
            "circles" : circles
            }

        return data

class subnet:
    def __init__(self, addr, mask, lat, long, name):
        self.addr = ip2long(addr)
        self.mask = ip2long(mask)
        self.lat = lat
        self.long = long
        self.name = name

    def match(self, a):
        return ((ip2long(a) & self.mask) == self.addr)

try:
    geolite_dat = os.path.expanduser('/tmp/GeoLiteCity.dat')
    gi = pygeoip.GeoIP(geolite_dat, pygeoip.MEMORY_CACHE)
    gi_lock = threading.Lock()
except IOError:
    # need to install GeoLiteCity
    print 'Geo database not found at /tmp/GeoLiteCity.dat'
    print 'Downloads may be found here: http://dev.maxmind.com/geoip/geolite#Downloads-5'
    print 'GeoIP support will be disabled without this file.'

