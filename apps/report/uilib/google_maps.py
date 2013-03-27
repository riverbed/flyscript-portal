# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
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

def MapWidget(widget, data):
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

rvbd_nets = (
    subnet('10.0.0.0', '255.255.0.0', 37.789294,-122.390152, '360 Spear'),
    subnet('10.1.0.0', '255.255.0.0', 37.788811, -122.390592, '365 Main'),
    subnet('10.16.0.0', '255.255.0.0', 37.788811, -122.390592, '365 Main'),
    subnet('10.32.0.0', '255.255.0.0', 37.78993,-122.39483, 'Headquarters'),
    subnet('10.35.0.0', '255.255.0.0',  37.388777,-122.038182, 'Sunnyvale'),
    subnet('10.38.0.0', '255.255.0.0', 42.394083, -71.14244, 'Cambridge'),
    subnet('10.100.0.0', '255.255.0.0', 42.394083, -71.14244, 'Cambridge'),
    subnet('10.37.0.0', '255.255.0.0', 40.089596, -88.240256, 'Illinois'),
    subnet('10.65.0.0', '255.255.0.0', 48.153203, 11.680355, 'Munich'),
    subnet('10.36.0.0', '255.255.0.0', 40.750151,-73.992823, 'New York City'),
    subnet('10.72.0.0', '255.255.0.0', 1.303913,103.835392, 'Singapore'),
    subnet('10.63.0.0', '255.255.0.0', 51.418305,-0.765181, 'Bracknell'),
    subnet('10.17.44.0', '255.255.252.0', 38.998767,-76.894276, 'Greenbelt'),
    subnet('10.17.48.0', '255.255.252.0', 38.550918,-121.722304, 'Davis'),
    subnet('10.2.8.0', '255.255.252.0',  37.388777,-122.038182, 'Sunnyvale Lab'),
)

try:
    geolite_dat = os.path.expanduser('/tmp/GeoLiteCity.dat')
    gi = pygeoip.GeoIP(geolite_dat, pygeoip.MEMORY_CACHE)
    gi_lock = threading.Lock()
except IOError:
    # need to install GeoLiteCity
    print 'Geo database not found at /tmp/GeoLiteCity.dat'
    print 'Downloads may be found here: http://dev.maxmind.com/geoip/geolite#Downloads-5'
    print 'GeoIP support will be disabled without this file.'

def geoip(addr, custom_nets=rvbd_nets):
    
    print "looking up %s" % addr
    data = { 'addr' : addr, 'internal' : 0 }

    with gi_lock:
        r = gi.record_by_addr(addr)

    match = False
    if r is not None:
        data['latitude'] = r['latitude']
        data['longitude'] = r['longitude']
        match = True
        try:
            (n, x, y) = socket.gethostbyaddr(addr)
            data['note'] = n
            if n.endswith('.riverbed.com'):
                data['internal'] = 1
        except:
            data['note'] = addr
    elif custom_nets:
        for n in custom_nets:
            if n.match(addr):
                data['latitude'] = n.lat
                data['longitude'] = n.long
                data['note'] = 'Riverbed: %s' % n.name
                data['internal'] = 1
                match = True
                break

    if match:
        return data
    else:
        return None

    
