# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import time
import pickle
import logging
import threading

from rvbd.shark import Shark
from rvbd.shark.types import Operation, Value, Key
from rvbd.shark.filters import SharkFilter, TimeFilter
from rvbd.shark._class_mapping import path_to_class
from rvbd.common.exceptions import RvbdHTTPException
from rvbd.common import timeutils


from apps.datasource.models import Column
from apps.datasource.devicemanager import DeviceManager
from project import settings
from libs.options import Options

logger = logging.getLogger(__name__)
lock = threading.Lock()

def DeviceManager_new(*args, **kwargs):
    # Used by DeviceManger to create a Profiler instance
    return Shark(*args, **kwargs)


class TableOptions(Options):
    def __init__(self, view, filter=None, aggregated=False, *args, **kwargs):
        super(TableOptions, self).__init__(*args, **kwargs)
        self.view = view
        self.filter = filter
        self.aggregated = aggregated

class ColumnOptions(Options):
    def __init__(self, extractor, operation=None, *args, **kwargs):
        super(Options, self).__init__(*args, **kwargs)
        self.extractor = extractor
        self.operation = operation

class Table_Query:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        cachefile = os.path.join(settings.DATA_CACHE, "table-%s.cache" % self.table.id)
        if os.path.exists(cachefile):
            # XXXCJ This cachefile hack is temporary and is only good for testing to avoid actually
            # having to run the report every single time.
            logger.debug("Using cache file")
            f = open(cachefile, "r")
            self.data = pickle.load(f)
            f.close()
        else:
            logger.debug("Running new report")
            table = self.table
            options = table.get_options()

            shark = DeviceManager.get_device(table.device.id)

            columns = []
            for tc in table.get_columns():
                tc_options = tc.get_options()
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
            if options.filter:
                filters.append(SharkFilter(options.filter))

            if table.duration:
                filters.append(TimeFilter.parse_range("last %d m" % table.duration))

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

            f = open(cachefile, "w")
            pickle.dump(self.data, f)
            f.close()

        return True

    def parse_data(self):
        """ Reformat shark data results to be uniform tabular format
        """
        out = []
        for d in self.data:
            out.extend(x for x in d['vals'])
        self.data = out

