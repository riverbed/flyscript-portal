# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import time, datetime
import pickle
import logging
import threading

from rvbd.shark import Shark
from rvbd.shark.types import Operation, Value, Key
from rvbd.shark.filters import SharkFilter, TimeFilter
from rvbd.shark._class_mapping import path_to_class
from rvbd.common.exceptions import RvbdHTTPException
from rvbd.common import timeutils


from apps.datasource.models import Column, Device, Table
from apps.datasource.devicemanager import DeviceManager
from project import settings
from libs.options import Options

logger = logging.getLogger(__name__)
lock = threading.Lock()


def DeviceManager_new(*args, **kwargs):
    # Used by DeviceManger to create a Profiler instance
    return Shark(*args, **kwargs)


class TableOptions(Options):
    def __init__(self, view, aggregated=False, *args, **kwargs):
        super(TableOptions, self).__init__(*args, **kwargs)
        self.view = view
        self.aggregated = aggregated


class ColumnOptions(Options):
    def __init__(self, extractor, operation=None, *args, **kwargs):
        super(Options, self).__init__(*args, **kwargs)
        self.extractor = extractor
        self.operation = operation


class SharkTable:
    @classmethod
    def create(cls, name, devicename, view, duration, aggregated=False, filterexpr=None):
        device = Device.objects.get(name=devicename)
        options = TableOptions(view, aggregated).encode()
        t = Table(name=name, module=__name__, device=device, duration=duration,
                  filterexpr=filterexpr, options=options)
        t.save()
        return t


def create_shark_column(table, name, label=None, datatype='', units='', iskey=False, issortcol=False,
                        extractor=None, operation=None):
    c = Column.create(table, name, label=label, datatype=datatype, units=units, iskey=iskey, issortcol=issortcol)
    options = ColumnOptions(extractor, operation=operation)
    c.options = options.encode()
    c.save()
    return c


class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        table = self.table
        options = table.get_options()

        shark = DeviceManager.get_device(table.device.id)

        columns = []
        for tc in table.get_columns():
            tc_options = tc.get_options(__name__)
            if tc.iskey:
                c = Key(tc_options.extractor, description=tc.label)
            else:
                if tc_options.operation:
                    try:
                        operation = getattr(Operation, tc_options.operation)
                    except AttributeError:
                        operation = Operation.sum
                        print 'ERROR: Unknown operation attribute %s for column %s.' % (tc_options.operation,
                                                                                        tc.name)
                else:
                    operation = Operation.sum

                c = Value(tc_options.extractor, operation, description=tc.label)

            columns.append(c)

        sortcol=None
        if table.sortcol is not None:
            sortcol=table.sortcol.get_options().extractor

        # get source type from options
        try:
            with lock:
                source = path_to_class(shark, options.view)
        except RvbdHTTPException, e:
            source = None
            raise e

        filters = []
        filterexpr = self.job.combine_filterexprs(joinstr="&")
        if filterexpr:
            filters.append(SharkFilter(filterexpr))

        criteria = self.job.get_criteria()
        tf = TimeFilter(start=datetime.datetime.fromtimestamp(criteria.starttime),
                        end=datetime.datetime.fromtimestamp(criteria.endtime))
        filters.append(tf)

        if source is not None:
            with lock:
                view = shark.create_view(source, columns, filters=filters, sync=False)
                #sort_col=sortcol,
        else:
            # XXX raise other exception
            return None

        done = False
        logger.info("Waiting for report to complete")
        while not done:
            time.sleep(0.5)
            with lock:
                s = view.get_progress()
                self.job.progress = s
                self.job.save()
            done = (s == 100)

        # Retrieve the data
        with lock:
            self.data = view.get_data(aggregated=options.aggregated)
            view.close()

        if table.rows > 0:
            self.data = self.data[:table.rows]


        self.parse_data()

        return True

    def parse_data(self):
        """ Reformat shark data results to be uniform tabular format
        """
        out = []
        for d in self.data:
            out.extend(x for x in d['vals'])
        self.data = out

