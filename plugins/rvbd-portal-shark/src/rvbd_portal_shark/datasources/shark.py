# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import time
import logging
import threading

from django import forms

from rvbd.shark import Shark
from rvbd.shark.types import Operation, Value, Key
from rvbd.shark.filters import SharkFilter, TimeFilter
from rvbd.shark._class_mapping import path_to_class
from rvbd.common.exceptions import RvbdHTTPException
from rvbd.common.jsondict import JsonDict
from rvbd.common import timeutils
from rvbd.common.timeutils import (parse_timedelta, datetime_to_seconds, 
                                   timedelta_total_seconds)

from rvbd_portal.apps.devices.models import Device
from rvbd_portal.apps.devices.devicemanager import DeviceManager
from rvbd_portal.apps.devices.forms import fields_add_device_selection
from rvbd_portal.apps.datasource.models import Column, Table, TableField
from rvbd_portal.apps.datasource.forms import fields_add_time_selection, fields_add_resolution

from rvbd_portal.libs.fields import Function

logger = logging.getLogger(__name__)
lock = threading.Lock()


def new_device_instance(*args, **kwargs):
    # Used by DeviceManger to create a Shark instance
    shark = Shark(*args, **kwargs)
    return shark


class TableOptions(JsonDict):
    _default = {'aggregated': False}


class ColumnOptions(JsonDict):
    _default = {'extractor': None,
                'operation': None,
                'default_value': None}


def fields_add_filterexpr(obj,
                          keyword = 'shark_filterexpr',
                          initial=None):
    field = ( TableField
              (keyword = keyword,
               label = 'Shark Filter Expression',
               help_text = 'Traffic expression using Shark filter syntax',
               initial = initial,
               required = False))
    field.save()
    obj.fields.add(field)

class SharkTable:
    @classmethod
    def create(cls, name, duration,
               aggregated=False, filterexpr=None, resolution='1min', sortcol=None):
        """ Create a Shark table.

        `duration` is in minutes

        """
        logger.debug('Creating Shark table %s (%s)' % (name, duration))
        options = TableOptions(aggregated=aggregated)
        
        t = Table(name=name, module=__name__, 
                  filterexpr=filterexpr, options=options, sortcol=sortcol)
        t.save()

        if resolution not in ['1ms', '1sec', '1min', '15min']:
            raise KeyError("Invalid resolution %s, must be one of: %s" %
                           (resolution, ', '.join(['1ms', '1sec', '1min', '15min'])))

        if isinstance(duration, int):
            duration = "%d min" % duration

        fields_add_device_selection(t,
                                    keyword='shark_device',
                                    label='Shark',
                                    module='shark',
                                    enabled=True)

        #TableField.create(keyword='shark_source_type', label='Source Type', obj=t,
        #                  field_cls = forms.ChoiceField,
        #                  field_kwargs = {'choices': [('job', 'Capture Job'),
        #                                              ('clip', 'Trace Clip')]})
        
        TableField.create(keyword='shark_source_name', label='Source', obj=t,
                          field_cls = forms.ChoiceField,
                          parent_keywords = ['shark_device'],
                          #parent_keywords = ['shark_device', 'shark_source_type'],
                          dynamic=True,
                          pre_process_func = Function(shark_source_name_choices))
        
        fields_add_time_selection(t, initial_duration=duration)
        fields_add_filterexpr(t)
        fields_add_resolution(t, initial=resolution,
                              resolutions = [('1sec', '1 second'),
                                             ('1min', '1 minute'),
                                             ('15min', '15 minutes')])
        return t


def shark_source_name_choices(form, id, field_kwargs, params):
    shark_device = form.get_field_value('shark_device', id)
    if shark_device == '':
        label = 'Source'
        choices = [('', '<No shark device>')]
    else:
        shark = DeviceManager.get_device(shark_device)
        #source_type = form.get_field_value('shark_source_type', id)
        source_type = 'job'

        choices = []
        if source_type == 'job':
            for job in shark.get_capture_jobs():
                choices.append (('jobs/' + job.name, job.name))
            label = 'Capture Job'
        elif source_type == 'clip':
            # Not tested
            label = 'Trace Clip'
            for clip in shark.get_clips():
                choices.append ((clip, clip))
        else:
            raise KeyError('Unknown source type: %s' % source_type)
        
    field_kwargs['label'] = label
    field_kwargs['choices'] = choices
            
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

        # Resolution comes in as a time_delta
        resolution = timedelta_total_seconds(job.criteria.resolution)

        default_delta = 1000000000                      # one second
        self.delta = int(default_delta * resolution)    # sample size interval


    def fake_run(self):
        import fake_data
        self.data = fake_data.make_data(self.table, self.job)

    def run(self):
        """ Main execution method
        """
        criteria = self.job.criteria

        if criteria.shark_device == '':
            logger.debug('%s: No shark device selected' % (self.table))
            self.job.mark_error("No Shark Device Selected")
            return False
            
        #self.fake_run()
        #return True
    
        shark = DeviceManager.get_device(criteria.shark_device)

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
        criteria = self.job.criteria

        filters = []
        filterexpr = self.job.combine_filterexprs(exprs=criteria.shark_filterexpr, joinstr="&")
        if filterexpr:
            filters.append(SharkFilter(filterexpr))

        tf = TimeFilter(start=criteria.starttime, end=criteria.endtime)
        filters.append(tf)

        logger.info("Setting shark table %d timeframe to %s" % (self.table.id, str(tf)))

        # process Report/Table Criteria
        self.table.apply_table_criteria(criteria)

        # Get source type from options
        try:
            with lock:
                source = path_to_class(shark, self.job.criteria.shark_source_name)

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
                if d['t'] is not None:
                    t = timeutils.datetime_to_microseconds(d['t']) / float(10 ** 6)
                    out.extend([t] + x for x in d['vals'])

        else:
            for d in self.data:
                out.extend(x for x in d['vals'])

        self.data = out
