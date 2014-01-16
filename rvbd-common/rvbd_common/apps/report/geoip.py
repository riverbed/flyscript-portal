# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
import json
from math import sin,cos
from rvbd.common import UserAuth
from rvbd.profiler import Profiler
from rvbd.profiler.filters import TimeFilter, TrafficFilter

import pygeoip
from pygeoip.util import ip2long
import json
import socket
import threading
import os.path

geolite_dat = os.path.expanduser('/ws/flyscript/examples/web/GeoLiteCity.dat')

class subnet:
    def __init__(self, addr, mask, lat, long, name):
        self.addr = ip2long(addr)
        self.mask = ip2long(mask)
        self.lat = lat
        self.long = long
        self.name = name

    def match(self, a):
        return ((pygeoip.ip2long(a) & self.mask) == self.addr)

rvbd_nets = (
    subnet('10.0.0.0', '255.255.0.0', 37.789294,-122.390152, '360 Spear'),
    subnet('10.1.0.0', '255.255.0.0', 37.788811, -122.390592, '365 Main'),
    subnet('10.16.0.0', '255.255.0.0', 37.788811, -122.390592, '365 Main'),
    subnet('10.32.0.0', '255.255.0.0', 37.78993,-122.39483, 'Headquarters'),
    subnet('10.35.0.0', '255.255.0.0',  37.388777,-122.038182, 'Sunnyvale'),
    subnet('10.38.0.0', '255.255.0.0', 42.394083, -71.14244, 'Cambridge'),
    subnet('10.37.0.0', '255.255.0.0', 40.089596, -88.240256, 'Illinois'),
    subnet('10.65.0.0', '255.255.0.0', 48.153203, 11.680355, 'Munich'),
    subnet('10.36.0.0.', '255.255.0.0', 40.750151,-73.992823, 'New York City'),
    subnet('10.72.0.0', '255.255.0.0', 1.303913,103.835392, 'Singapore'),
    subnet('10.63.0.0', '255.255.0.0', 51.418305,-0.765181, 'Bracknell'),
    subnet('10.17.44.0', '255.255.252.0', 38.998767,-76.894276, 'Greenbelt'),
    subnet('10.17.48.0', '255.255.252.0', 38.550918,-121.722304, 'Davis'),
    subnet('10.2.8.0', '255.255.252.0',  37.388777,-122.038182, 'Sunnyvale Lab'),
)

def test(request):
    return HttpResponse("Test succeeded")

p = Profiler("eng-profiler.lab.nbttech.com", auth=UserAuth("admin", "admin"))
print "connected"

def data(request):
    report = p.create_traffic_overall_time_series_report(
        columns = [p.columns.key.time,
                   p.columns.value.avg_bytes,
                   p.columns.value.network_rtt],
        sort_col = p.columns.key.time,
        timefilter = TimeFilter.parse_range("last 15 m"),
        trafficexpr = TrafficFilter("host 10/8")
        )
    rdata = report.get_data()
    print "rdata: %s" % rdata
    s1 = []
    for row in rdata:
        s1.append({"x": int(row[0] - rdata[0][0]), "y": int(row[1]/1000000)})

    print "s1: %s" % s1
    data = {
        "xaxis" : "Time",
        "yaxis" : "BW",
        "width" : "600px",
        "height" : "300px",
        "data" : [ { "values" : s1,                                  
                     "key" : "Data 1",
                     "color" : "#ff7f0e"
                     }
                   ]
        }
    return HttpResponse(json.dumps(data))

def mapdata(request):
    report = p.create_traffic_summary_report(
        groupby = p.groupbys.host_pair,
        columns = [p.columns.key.cli_host_ip,
                   p.columns.key.srv_host_ip,
                   p.columns.value.avg_bytes],
        sort_col = p.columns.value.avg_bytes,
        timefilter = TimeFilter.parse_range("last 5 m"),
        trafficexpr = TrafficFilter("host 10/8")
        )
    rdata = report.get_data()
    print "rdata: %s" % rdata
    data = []
    for row in rdata[:-10]:
        data.append({"x0": row[0],
                     "x1" : row[1],
                     "x2" : str(row[2])})

    return HttpResponse(json.dumps(data))

gi = pygeoip.GeoIP(geolite_dat, pygeoip.MEMORY_CACHE)
gi_lock = threading.Lock()

def geo(request, addr):
    print "GEO request for %s" % addr
    D = { 'addr' : addr, 'internal' : 0 }

    with gi_lock:
        r = gi.record_by_addr(addr)

    if r is not None:
        D['latitude'] = r['latitude']
        D['longitude'] = r['longitude']
        try:
            (n, x, y) = socket.gethostbyaddr(addr)
            D['note'] = n
            if n.endswith('.riverbed.com'):
                D['internal'] = 1
        except:
            D['note'] = addr

    else:
        for n in rvbd_nets:
            if n.match(addr):
                D['latitude'] = n.lat
                D['longitude'] = n.long
                D['note'] = 'Riverbed: %s' % n.name
                D['internal'] = 1

    if 'latitude' not in D:
        start_response('404 Not Found', [('Content-type', 'text/plain')])
        return [ 'Cannot lookup %s' % addr ]

    data = json.dumps(D)
    return HttpResponse(data)

    
