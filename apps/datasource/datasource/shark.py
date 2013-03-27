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


from apps.datasource.models import TableColumn
from apps.datasource.devicemanager import DeviceManager
from project import settings

logger = logging.getLogger('datasource')
lock = threading.Lock()


def DeviceManager_new(*args, **kwargs):
    # Used by DeviceManger to create a Profiler instance
    return Shark(*args, **kwargs)


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

            shark = DeviceManager.get_device(table.options['device'])

            columns = []
            for tc in TableColumn.objects.filter(table=table).select_related():
                if tc.column.source_key:
                    c = Key(tc.column.source_name, description=tc.column.label)
                else:
                    if tc.column.source_operation:
                        try:
                            operation = getattr(Operation, tc.column.source_operation)
                        except AttributeError:
                            operation = Operation.sum
                            print 'ERROR: Unknown operation attribute %s for column %s.' % (tc.column.source_operation,
                                                                                            tc.column.name)
                    else:
                        operation = Operation.sum

                    c = Value(tc.column.source_name, operation, description=tc.column.label)

                columns.append(c)

            sortcol=None
            if table.sortcol is not None:
                sortcol=table.sortcol.source_name

            # get source type from options
            try:
                with lock:
                    source = path_to_class(shark, table.options['view'])
            except RvbdHTTPException, e:
                source = None
                raise e

            filters = []
            if 'filter' in table.options:
                filters.append(SharkFilter(table.options['filter']))

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
            if 'aggregated' in table.options:
                aggregated = table.options['aggregated']
            else:
                aggregated = False
            with lock:
                self.data = view.get_data(aggregated=aggregated)
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
