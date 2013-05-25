# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import pygeoip
from pygeoip.util import ip2long
import threading
import os.path

from apps.report.models import Widget
from apps.geolocation.models import Location
from apps.geolocation.geoip import Lookup

class MapWidget:
    @classmethod
    def create(cls, report, table, title, width=6, height=300, column=None):
        """Class method to create a MapWidget.

        `column` is the data column to graph
        """

        w = Widget(report=report, title=title, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey == True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))

        column  = column or [col.name for col in table.get_columns() if col.iskey == False][0]
            
        w.options = { 'key' : keycols[0],
                      'value': column }
        w.save()
        w.tables.add(table)
        
    
    @classmethod
    def process(cls, widget, data):
        """Class method to generate JSON for the JavaScript-side of the MapWidget
        from the incoming data.
        """
        columns = widget.table().get_columns()

        class ColInfo:
            def __init__(self, col, dataindex):
                self.col = col
                self.dataindex = dataindex

        keycol = None
        valuecol = None
        for i in range(len(columns)):
            c = columns[i]
            if c.name == widget.get_option('key'):
                keycol = ColInfo(c, i)
            elif c.name == widget.get_option('value'):
                valuecol = ColInfo(c, i)
        
        # Array of google circle objects for each data row
        circles = []
        if data:
            valmin = data[0][valuecol.dataindex]
            valmax = valmin
            
            for reportrow in data:
                val = reportrow[1]
                valmin = min(val, valmin)
                valmax = max(val, valmax)

            geolookup = None

            if valuecol.col.datatype == 'bytes':
                formatter = 'formatBytes'
            elif valuecol.col.datatype == 'metric':
                formatter = 'formatMetric'
            else:
                formatter = None;

            for reportrow in data:
                key = reportrow[keycol.dataindex]
                val = reportrow[valuecol.dataindex]
 
                # XXXCJ - this is a hack for Profiler based host groups,
                # need to find a way to generalize this, probably via options
                if widget.table().options['groupby'] == 'host_group':
                    geo = Location.objects.get(name=key)
                else:
                    # Perform geolookup on the key (should be an IP address...)
                    if geolookup == None:
                        geolookup = Lookup.instance()
                    geo = geolookup.lookup(key)

                if geo:
                    # Found a match, create a circle with the size of the
                    # circle based on the where val falls in [min,max]
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
                        'units': valuecol.col.units,
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

