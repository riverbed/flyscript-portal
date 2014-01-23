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

from django.core.exceptions import ObjectDoesNotExist

from rvbd_portal.apps.report.models import Widget
from rvbd_portal.apps.geolocation.models import Location
from rvbd_portal.apps.geolocation.geoip import Lookup
from project.utils import get_request

from .maps_providers import google_postprocess, openstreetmaps_postprocess

POST_PROCESS_MAP = {'DISABLED': google_postprocess,
                    'DEVELOPER': google_postprocess,
                    'FREE': google_postprocess,
                    'BUSINESS': google_postprocess,
                    'OPEN_STREET_MAPS': openstreetmaps_postprocess,
                    'STATIC_MAPS': lambda x: x,
                    }


def authorized(userprofile):
    """ Verifies the Maps API can be used given the version selected
        and the API key supplied.

        Returns True/False, and an error message if applicable
    """
    maps_version = userprofile.maps_version
    api_key = userprofile.maps_api_key

    if maps_version == 'DISABLED':
        msg = (u'Maps API has been disabled.\n'
               'See Configure->Preferences to update.')
        return False, msg
    elif maps_version in ('FREE', 'BUSINESS') and not api_key:
        msg = (u'A valid API_KEY must be provided for either \n'
               '"Free" or "Business" Google Maps API choices.\n'
               'See Configure->Preferences to update.')
        return False, msg
    else:
        return True, ''


class MapWidgetOptions(JsonDict):
    _default = {'key': None,
                'value': None}
    _required = ['key', 'value']


class MapWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, height=300, column=None):
        """Class method to create a MapWidget.

        `column` is the data column to graph, defaults to the first non-key
                 column found assigned to the table.
        """
        w = Widget(section=section, title=title, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))

        column = column or [col.name for col in table.get_columns() if col.iskey is False][0]

        w.options = MapWidgetOptions(key=keycols[0], value=column)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        """Class method to generate list of circle objects.

        Subclass should manipulate this list into specific JSON structures as needed.
        """

        request = get_request()
        maps_version = request.user.userprofile.maps_version
        post_process = POST_PROCESS_MAP[maps_version]

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
            values = zip(*data)[valuecol.dataindex]
            filtered = filter(bool, values)
            if filtered:
                valmin = min(filtered)
                valmax = max(filtered)

            geolookup = None

            if valuecol.col.datatype == 'bytes':
                formatter = 'formatBytes'
            elif valuecol.col.datatype == 'metric':
                formatter = 'formatMetric'
            else:
                formatter = None

            for rawrow in data:
                key = rawrow[keycol.dataindex]
                val = rawrow[valuecol.dataindex]

                # skip empty result values which are not explicitly zero
                if val is None or val == '':
                    continue

                # XXXCJ - this is a hack for Profiler based host groups,
                # need to find a way to generalize this, probably via options
                if widget.table().options['groupby'] == 'host_group':
                    try:
                        geo = Location.objects.get(name=key)
                    except ObjectDoesNotExist:
                        continue
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
            "chartTitle": widget.title.format(**job.actual_criteria),
            "circles": circles
        }

        return post_process(data)


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
