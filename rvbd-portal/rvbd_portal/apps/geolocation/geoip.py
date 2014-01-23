# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import socket
import threading

import pygeoip
from pygeoip.util import ip2long
from rvbd.common.utils import DictObject

from rvbd_portal.apps.geolocation.models import Location


GEOLOCATION_DATA_FILE = '/tmp/GeoLiteCity.dat1'
lookup_lock = threading.Lock()

class Lookup(object):
    _singleton = None
    
    def __init__(self):
        if not os.path.exists(GEOLOCATION_DATA_FILE):
            raise ValueError("Please download the city database from http://dev.maxmind.com/geoip/install/city and save at %s" % GEOLOCATION_DATA_FILE)
        
        geolite_dat = os.path.expanduser(GEOLOCATION_DATA_FILE)
        self.geoip = pygeoip.GeoIP(geolite_dat, pygeoip.MEMORY_CACHE)

    @classmethod
    def instance(cls):
        with lookup_lock:
            if cls._singleton is None:
                cls._singleton = Lookup()

        return cls._singleton

    def lookup(self, addr):
        data = DictObject()
        data.addr = addr
        data.internal = False

        with lookup_lock:
            r = self.geoip.record_by_addr(addr)

        match = False

        if r is not None:
            data.latitude = r['latitude']
            data.longitude = r['longitude']
            match = True
            try:
                (n, x, y) = socket.gethostbyaddr(addr)
                data.name = n
            except:
                data.name = None

        else:
            addrlong = ip2long(addr)
            
            for location in Location.objects.all():
                if ((addrlong & ip2long(location.mask)) == ip2long(location.address)):
                    data.latitude = location.latitude
                    data.longitude = location.longitude
                    data.name = location.name
                    data.internal = True
                    match = True
                    break

        if match:
            return data
        else:
            return None


