# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import datetime

from rvbd.common.timeutils import datetime_to_seconds

from rvbd_portal.apps.report.models import Widget

import logging
logger = logging.getLogger(__name__)


class TableWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=1000, height=300):
        w = Widget(section=section, title=title, rows=rows, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        newdata = []
        for row in data:
            newrow = []
            for col in row:
                if isinstance(col, datetime.datetime):
                    col = datetime_to_seconds(col)
                newrow.append(col)
            newdata.append(newrow)
        
        return newdata
