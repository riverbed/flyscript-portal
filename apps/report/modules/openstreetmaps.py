# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

"""
This module renders raw data from a data source to be displayed
using the OpenStreetMap API
"""

from .maps_base import BaseMapWidget, subnet


def authorized(userprofile):
    """ Verifies the OpenStreetMap API can be used given the version selected
        and the API key supplied.

    """
    # XXX For now returns True until API key questions sorted out

    return True, ''


class MapWidget(BaseMapWidget):
    @classmethod
    def create(cls, report, table, title, width=6, height=300, column=None):
        """Class method to create a MapWidget.

        `column` is the data column to graph
        """
        super(MapWidget, cls).create(report, table, title, width, height, column,
                                     module=__name__, uiwidget=cls.__name__)

    @classmethod
    def process(cls, widget, data):
        """Class method to generate JSON for the JavaScript-side of the MapWidget
        from the incoming data.
        """
        data = super(MapWidget, cls).process(widget, data)

        circles = []
        for c in data['circles']:
            circle = {
                'center': [c.lat, c.long],
                'stroke': True,
                'color': '#FF0000',
                'weight': 2,
                'opacity': 0.8,
                'fillColor': '#FF0000',
                'fillOpacity': 0.35,
                'clickable': False,

                'radius': 15 * (c.value / c.value_max),
                'title': c.title,

                'value': c.value,
                'units': c.units,
                'formatter': c.formatter
            }
            circles.append(circle)
        data['circles'] = circles

        return data
