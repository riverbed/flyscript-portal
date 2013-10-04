# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import time
import logging
import datetime
import threading

import pandas as pd
from rvbd.shark import Shark
from rvbd.shark.types import Operation, Value, Key
from rvbd.shark.filters import SharkFilter, TimeFilter
from rvbd.shark._class_mapping import path_to_class
from rvbd.common.exceptions import RvbdHTTPException
from rvbd.common.jsondict import JsonDict
from rvbd.common import timeutils

from apps.datasource.models import Column, Table
from apps.devices.devicemanager import DeviceManager

logger = logging.getLogger(__name__)
lock = threading.Lock()


def new_device_instance(*args, **kwargs):
    # Used by DeviceManger to create a Shark instance
    shark = Shark(*args, **kwargs)
    return shark


class TableOptions(JsonDict):
    _default = {'view': None,
                'view_size': '10%',
                'aggregated': False}


class ColumnOptions(JsonDict):
    _default = {'extractor': None,
                'operation': None,
                'default_value': None}


class SharkTable:
    @classmethod
    def create(cls, name, device, view, view_size, duration,
               aggregated=False, filterexpr=None, resolution=60, sortcol=None):
        logger.debug('Creating Shark table %s (%s, %d)' % (name, view, duration))
        options = TableOptions(view=view,
                               view_size=view_size,
                               aggregated=aggregated)
        t = Table(name=name, module=__name__, device=device, duration=duration,
                  filterexpr=filterexpr, options=options, resolution=resolution,
                  sortcol=sortcol)
        t.save()
        return t


def create_shark_column(table, name, label=None, datatype='', units='', iskey=False,
                        issortcol=False, extractor=None, operation=None, default_value=None):
    options = ColumnOptions(extractor=extractor,
                            operation=operation,
                            default_value=default_value)
    c = Column.create(table, name, label=label, datatype=datatype, units=units,
                      iskey=iskey, issortcol=issortcol, options=options)
    c.save()
    return c


def setup_capture_job(shark, name, size=None):
    if size is None:
        size = '10%'

    try:
        job = shark.get_capture_job_by_name(name)
    except ValueError:
        # create a capture job on the first available interface
        interface = shark.get_interfaces()[0]
        job = shark.create_job(interface, name, size, indexing_size_limit='2GB',
                               start_immediately=True)
    return job


class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job
        self.timeseries = False         # if key column called 'time' is created
        self.column_names = []

        default_delta = 1000000000                      # one second
        self.delta = default_delta * table.resolution   # sample size interval

    def run(self):
        """ Main execution method
        """

        shark = DeviceManager.get_device(self.table.device.id)

        logger.debug("Creating columns for Shark table %d" % self.table.id)

        # Create Key/Value Columns
        columns = []
        for tc in self.table.get_columns(synthetic=False):
            tc_options = tc.options
            if tc.iskey and tc.name == 'time' and tc_options.extractor == 'sample_time':
                # don't create column for view, we will use the sample time for timeseries
                self.timeseries = True
                self.column_names.append('time')
                continue
            elif tc.iskey:
                c = Key(tc_options.extractor, 
                        description=tc.label,
                        default_value=tc_options.default_value)
            else:
                if tc_options.operation:
                    try:
                        operation = getattr(Operation, tc_options.operation)
                    except AttributeError:
                        operation = Operation.sum
                        print ('ERROR: Unknown operation attribute '
                               '%s for column %s.' % (tc_options.operation, tc.name))
                else:
                    operation = Operation.none

                c = Value(tc_options.extractor,
                          operation,
                          description=tc.label,
                          default_value=tc_options.default_value)
                self.column_names.append(tc.name)

            columns.append(c)

        # Identify Sort Column
        sortidx = None
        if self.table.sortcol is not None:
            sort_name = self.table.sortcol.options.extractor
            for i, c in enumerate(columns):
                if c.field == sort_name:
                    sortidx = i
                    break

        # Initialize filters
        filters = []
        filterexpr = self.job.combine_filterexprs(joinstr="&")
        if filterexpr:
            filters.append(SharkFilter(filterexpr))

        criteria = self.job.criteria
        tf = TimeFilter(start=datetime.datetime.fromtimestamp(criteria.starttime),
                        end=datetime.datetime.fromtimestamp(criteria.endtime))
        filters.append(tf)

        logger.info("Setting shark table %d timeframe to %s" % (self.table.id, str(tf)))

        # process Report/Table Criteria
        self.table.apply_table_criteria(criteria)

        # Get source type from options
        try:
            with lock:
                source = path_to_class(shark, self.table.options.view)
                setup_capture_job(shark, 
                                  self.table.options.view.split('/', 1)[1],
                                  self.table.options.view_size)
        except RvbdHTTPException, e:
            source = None
            raise e

        # Setup the view
        if source is not None:
            with lock:
                view = shark.create_view(source, columns, filters=filters, sync=False)
        else:
            # XXX raise other exception
            return None

        done = False
        logger.debug("Waiting for shark table %d to complete" % self.table.id)
        while not done:
            time.sleep(0.5)
            with lock:
                s = view.get_progress()
                self.job.progress = s
                self.job.save()
            done = (s == 100)

        # Retrieve the data
        with lock:
            if self.table.options.aggregated:
                self.data = view.get_data(aggregated=self.table.options.aggregated, 
                                          sortby=sortidx)
            else:
                self.data = view.get_data(delta=self.delta, sortby=sortidx)
            view.close()

        if self.table.rows > 0:
            self.data = self.data[:self.table.rows]

        self.parse_data()

        logger.info("Shark Report %s returned %s rows" % (self.job, len(self.data)))

        return True

    def parse_data(self):
        """ Reformat shark data results to be uniform tabular format
        """
        out = []
        if self.timeseries:
            # use sample times for each row
            for d in self.data:
                t = timeutils.datetime_to_microseconds(d['t']) / float(10 ** 6)
                out.extend([t] + x for x in d['vals'])

        else:
            for d in self.data:
                out.extend(x for x in d['vals'])

        self.data = out
