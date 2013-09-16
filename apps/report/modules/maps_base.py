# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

"""
This module provides base mapping classes for specific APIs to leverage
"""

import os.path
import threading
from collections import namedtuple

import pygeoip
from pygeoip.util import ip2long

from rvbd.common.jsondict import JsonDict

from apps.report.models import Widget
from apps.geolocation.models import Location
from apps.geolocation.geoip import Lookup


class BaseMapWidgetOptions(JsonDict):
    _default = {'key': None,
                'value': None}
    _required = ['key', 'value']


class BaseMapWidget(object):
    @classmethod
    def create(cls, report, table, title, width=6, height=300, column=None,
               module=None, uiwidget=None):
        """Class method to create a MapWidget.

        `column` is the data column to graph
        """
        if module is None:
            module = __name__
        if uiwidget is None:
            uiwidget = cls.__name__

        w = Widget(report=report, title=title, width=width, height=height,
                   module=module, uiwidget=uiwidget)
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))

        column = column or [col.name for col in table.get_columns() if col.iskey is False][0]

        w.options = BaseMapWidgetOptions(key=keycols[0], value=column)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, data):
        """Class method to generate list of circle objects.

        Subclass should manipulate this list into specific JSON structures as needed.
        """
        columns = widget.table().get_columns()

        ColInfo = namedtuple('ColInfo', ['col', 'dataindex'])

        keycol = None
        valuecol = None
        for i, c in enumerate(columns):
            if c.name == widget.options.key:
                keycol = ColInfo(c, i)
            elif c.name == widget.options.value:
                valuecol = ColInfo(c, i)

        # Array of circle objects for each data row
        Circle = namedtuple('Circle', ['title', 'lat', 'long', 'value', 'value_max',
                                       'units', 'formatter'])
        circles = []

        if data:
            valmin = data[0][valuecol.dataindex]
            valmax = valmin

            for reportrow in data:
                val = reportrow[valuecol.dataindex]
                valmin = min(val, valmin)
                valmax = max(val, valmax)

            geolookup = None

            if valuecol.col.datatype == 'bytes':
                formatter = 'formatBytes'
            elif valuecol.col.datatype == 'metric':
                formatter = 'formatMetric'
            else:
                formatter = None

            for reportrow in data:
                key = reportrow[keycol.dataindex]
                val = reportrow[valuecol.dataindex]

                # XXXCJ - this is a hack for Profiler based host groups,
                # need to find a way to generalize this, probably via options
                if widget.table().options['groupby'] == 'host_group':
                    geo = Location.objects.get(name=key)
                else:
                    # Perform geolookup on the key (should be an IP address...)
                    if geolookup is None:
                        geolookup = Lookup.instance()
                    geo = geolookup.lookup(key)

                if geo:
                    # Found a match, create a Circle
                    circle = Circle(title=geo.name,
                                    lat=geo.latitude,
                                    long=geo.longitude,
                                    value=val,
                                    value_max=valmax,
                                    units=valuecol.col.units,
                                    formatter=formatter)
                    circles.append(circle)
        else:
            # no data just return empty circles list
            pass

        data = {
            "chartTitle": widget.title,
            "circles": circles
        }

        return data


class subnet(object):
    def __init__(self, addr, mask, lat, lng, name):
        self.addr = ip2long(addr)
        self.mask = ip2long(mask)
        self.lat = lat
        self.long = lng
        self.name = name

    def match(self, a):
        return (ip2long(a) & self.mask) == self.addr

try:
    geolite_dat = os.path.expanduser('/tmp/GeoLiteCity.dat')
    gi = pygeoip.GeoIP(geolite_dat, pygeoip.MEMORY_CACHE)
    gi_lock = threading.Lock()
except IOError:
    # need to install GeoLiteCity
    print 'Geo database not found at /tmp/GeoLiteCity.dat'
    print 'Downloads may be found here: http://dev.maxmind.com/geoip/geolite#Downloads-5'
    print 'GeoIP support will be disabled without this file.'
