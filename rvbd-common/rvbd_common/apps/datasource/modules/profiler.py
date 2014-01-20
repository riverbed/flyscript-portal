# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import time
import logging
import threading
import datetime

import rvbd.profiler
from rvbd.profiler.filters import TimeFilter, TrafficFilter
from rvbd.common.jsondict import JsonDict
from rvbd.common.timeutils import (parse_timedelta, timedelta_total_seconds)

from rvbd_common.apps.datasource.models import Table, TableField
from rvbd_common.apps.devices.models import Device
from rvbd_common.apps.devices.forms import fields_add_device_selection
from rvbd_common.apps.devices.devicemanager import DeviceManager
from rvbd_common.apps.datasource.forms import fields_add_time_selection, fields_add_resolution
from rvbd_common.libs.fields import Function

logger = logging.getLogger(__name__)
lock = threading.Lock()

def new_device_instance(*args, **kwargs):
    # Used by DeviceManager to create a Profiler instance
    return rvbd.profiler.Profiler(*args, **kwargs)


def fields_add_filterexpr(obj,
                          keyword = 'profiler_filterexpr',
                          initial=None
                          ):
    field = ( TableField
              (keyword = keyword,
               label = 'Profiler Filter Expression',
               help_text = ('Traffic expression using Profiler Advanced ' +
                            'Traffic Expression syntax'),
               initial = initial,
               required = False))
    field.save()
    obj.fields.add(field)

def fields_add_filterexprs_field(obj, keyword):
    field = obj.fields.get(keyword = 'profiler_filterexpr')
    field.post_process_func = Function(function=_fields_combine_filterexprs)

    parent_keywords = set(field.parent_keywords or [])
    parent_keywords.add(keyword)
    field.parent_keywords = list(parent_keywords)
    field.save()
    
    return field
    
def _fields_combine_filterexprs(field, criteria, params):
    exprs = []
    if (  'profiler_filterexpr' in criteria and
          criteria.profiler_filterexpr != ''):
        exprs.append(criteria.profiler_filterexpr)
    for parent in field.parent_keywords:
        expr = criteria[parent]
        if expr is not None and expr != '':
            exprs.append(expr)

    if len(exprs) == 0:
        val = ""
    elif len(exprs) == 1:
        val = exprs[0]
    else:
        val = "(" + (") and (").join(exprs) + ")"

    criteria['profiler_filterexpr'] = val

class TableOptions(JsonDict):
    _default = {'groupby': None,
                'realm': None,
                'centricity': None}


class ProfilerTable(object):
    @classmethod
    def create(cls, name, groupby, realm, duration,
               resolution='auto', filterexpr=None, interface=False,
               **kwargs):
        logger.debug('Creating ProfilerTable table %s (%s) - %s/%s' %
                     (name, duration, groupby, realm))

        options = TableOptions(groupby=groupby,
                               realm=realm,
                               centricity='int' if interface else 'hos')


        t = Table(name=name, module=__name__, 
                  filterexpr=filterexpr, options=options, **kwargs)
        t.save()

        if resolution != 'auto':
            if isinstance(resolution, int):
                rsecs = resolution
            else:
                rsecs  = int(timedelta_total_seconds(parse_timedelta(resolution)))
            resolution = rvbd.profiler.report.Report.RESOLUTION_MAP[rsecs]

        if isinstance(duration, int):
            duration = "%d min" % duration

        fields_add_device_selection(t, keyword='profiler_device', label='Profiler',
                                    module='profiler', enabled=True)
        fields_add_time_selection(t, initial_duration=duration)
        
        fields_add_filterexpr(t)
        fields_add_resolution(t, initial=resolution,
                              resolutions = [('auto', 'Automatic'),
                                             ('1min', '1 minute'),
                                             ('15min', '15 minutes'),
                                             ('hour', 'Hour'),
                                             ('6hour', '6 Hour')],
                              special_values = ['auto'])
        return t

class TimeSeriesTable(ProfilerTable):
    @classmethod
    def create(cls, name, duration,
               resolution='auto',
               filterexpr=None,
               interface=False,
               **kwargs):
        """ Create a Profiler TimeSeriesTable.

        `duration` is in minutes or a string like '15min'

        """
        logger.debug('Creating Profiler TimeSeries table %s (%s)' %
                     (name, duration))

        return super(TimeSeriesTable,cls).create(name,
                                                 groupby='time',
                                                 realm='traffic_overall_time_series',
                                                 duration=duration,
                                                 resolution=resolution,
                                                 filterexpr=filterexpr,
                                                 interface=interface,
                                                 **kwargs)
    
class GroupByTable(ProfilerTable):
    @classmethod
    def create(cls, name, groupby, duration, 
               resolution='auto',
               filterexpr=None,
               interface=False,
               **kwargs):
        """ Create a Profiler TimeSeriesTable.

        `duration` is in minutes

        """
        msg = 'Creating Profiler GroupBy table %s (%s, %s, %s)'
        logger.debug(msg % (name, groupby, duration, filterexpr))

        return super(GroupByTable,cls).create(name,
                                              groupby=groupby,
                                              realm='traffic_summary',
                                              duration=duration, 
                                              resolution=resolution,
                                              filterexpr=filterexpr,
                                              interface=interface,
                                              **kwargs)

class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def fake_run(self):
        import fake_data
        self.data = fake_data.make_data(self.table, self.job)
        
    def run(self):
        """ Main execution method
        """
        criteria = self.job.criteria

        if criteria.profiler_device == '':
            logger.debug('%s: No profiler device selected' % (self.table))
            self.job.mark_error("No Profiler Device Selected")
            return False
            
        #self.fake_run()
        #return True

        profiler = DeviceManager.get_device(criteria.profiler_device)
        report = rvbd.profiler.report.SingleQueryReport(profiler)

        columns = [col.name for col in self.table.get_columns(synthetic=False)]

        sortcol = None
        if self.table.sortcol is not None:
            sortcol = self.table.sortcol.name

        tf = TimeFilter(start=criteria.starttime,
                        end=criteria.endtime)

        logger.info("Running Profiler table %d report for timeframe %s" % (self.table.id,
                                                                           str(tf)))

        # process Report/Table Criteria
        self.table.apply_table_criteria(criteria)

        if ('datafilter' in criteria) and (criteria.datafilter is not None):
            datafilter = criteria.datafilter.split(',')
        else:
            datafilter = None

        trafficexpr = TrafficFilter(self.job.combine_filterexprs(exprs=criteria.profiler_filterexpr))

        # Incoming criteria.resolution is a timedelta
        logger.debug('Profiler report got criteria resolution %s (%s)' %
                     (criteria.resolution, type(criteria.resolution)))
        if criteria.resolution != 'auto':
            rsecs  = int(timedelta_total_seconds(criteria.resolution))
            resolution = rvbd.profiler.report.Report.RESOLUTION_MAP[rsecs]
        else:
            resolution = 'auto'
        
        logger.debug('Profiler report using resolution %s (%s)' % (resolution, type(resolution)))

        with lock:
            report.run(realm=self.table.options.realm,
                       groupby=profiler.groupbys[self.table.options.groupby],
                       centricity=self.table.options.centricity,
                       columns=columns,
                       timefilter=tf, 
                       trafficexpr=trafficexpr,
                       data_filter=datafilter,
                       resolution=resolution,
                       sort_col=sortcol,
                       sync=False
                       )

        done = False
        logger.info("Waiting for report to complete")
        while not done:
            time.sleep(0.5)
            with lock:
                s = report.status()

            self.job.safe_update(progress = int(s['percent']))
            done = (s['status'] == 'completed')

        # Retrieve the data
        with lock:
            query = report.get_query_by_index(0)
            self.data = query.get_data()

            tz = criteria.starttime.tzinfo
            # Update criteria
            criteria.starttime = (datetime.datetime
                                  .utcfromtimestamp(query.actual_t0)
                                  .replace(tzinfo=tz))
            criteria.endtime = (datetime.datetime
                                .utcfromtimestamp(query.actual_t1)
                                .replace(tzinfo=tz))

        self.job.safe_update(actual_criteria = criteria)

        if self.table.rows > 0:
            self.data = self.data[:self.table.rows]

        logger.info("Report %s returned %s rows" % (self.job, len(self.data)))
        return True
