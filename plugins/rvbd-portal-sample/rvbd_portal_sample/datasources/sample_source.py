# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging
import math

from rvbd.common.timeutils import \
    datetime_to_seconds, timedelta_total_seconds, parse_timedelta
from rvbd.common.jsondict import JsonDict

from rvbd_portal.apps.datasource.models import Table as BaseTable
from rvbd_portal.apps.datasource.models import TableField, Column
from rvbd_portal.apps.devices.forms import fields_add_device_selection
from rvbd_portal.apps.devices.devicemanager import DeviceManager
from rvbd_portal.apps.datasource.forms import (fields_add_time_selection,
                                               fields_add_resolution)

logger = logging.getLogger(__name__)


# ColumnOptions is a dictionary of options that
# are specific to columns for tables in this file.
# The column options are available when the query is run.
# The values are stored with the column definition at
# table / column defintiion time.
#
# Use of this class is entirely optional, it may be deleted
# if there are no custom column options
class ColumnOptions(JsonDict):
    _default = { 'func': 'sin',
                 'period': '1m',
                 'alpha': 1 }


# TableOptions is a dictionary of options that
# are specific to tables in this file.  This includes
# options that are common to every query run
#
# Use of this class is entirely optional, it may be deleted
# if there are no custom column options
class TableOptions(JsonDict):
    _default = { 'beta': 10 }


# Define a Table.create() method
class Table(object):


    # The arguments that create() accepts can be changed to whatever
    # is required by this Table
    @classmethod
    def create(cls, name, options, duration='1h', resolution='1min', **kwargs):

        # Create the table object and save it
        t = BaseTable(name=name, module=__name__, options=options, **kwargs)
        t.save()

        #
        # Add criteria fields that are required by this table
        #

        # Add a device selection criteria to the table,
        # listing only devices from sample_device module that are
        # enabled
        fields_add_device_selection(t, keyword='sample_device',
                                    label='Sample', module='sample_device',
                                    enabled=True)

        # Add a time selection field
        fields_add_time_selection(t, initial_duration=duration)

        # Add a time resolution field
        fields_add_resolution(t, initial=resolution,
                              resolutions=[('auto', 'Automatic'),
                                           '1sec', '1min', '15min', 'hour', '6hour'],
                              special_values=['auto'])

        # Add a custom field
        TableField.create(obj=t, keyword='min', initial=-100, label='Min value',
                          help_text=('Clip all wave forms at this minimum value'),
                          required=False)

        # Add a custom field
        TableField.create(obj=t, keyword='max', initial=100, label='Max value',
                          help_text=('Clip all wave forms at this maximum value'),
                          required=False)

        return t


# The TableQuery class must be defined with the __init__ and run
# method taking the defined arguments
class TableQuery(object):

    def __init__(self, table, job):
        self.table = table
        self.job = job

        # Perform any additional query initialization here

    # This method is called to actually execute the query
    # for the given table and job.  This is executed in a separate
    # thread and must not return until either the query completes
    # and data is available, or the query fails and returns an error.
    #
    # On success, this function should return either a list of lists
    # of data aligned to the set of non-synthetic columns associated
    # with this table or a pandas DataFrame with matching columns.
    # (synthetic columns are computed by automatically one the query
    # completes)
    #
    # On error, any errors that are not programmatic (like bad
    # criteria values) should be reported by calling
    # self.job.mark_error() with a user-friendly error message
    # indicating the cause of the failure.
    #
    # Any programmatic errors should be raised as exceptions.
    #
    # For long running queries self.job.mark_progress() should
    # be called to update the progress from 0 to 100 percent complete.
    def run(self):
        # All user entered criteria is available directly from this object.
        # Values for any fields added to the table will appear as
        # attributes according to the field keyword.
        criteria = self.job.criteria

        # Check that a sample_device was selected
        if criteria.sample_device == '':
            logger.debug('%s: No sample device selected' % self.table)
            self.job.mark_error("No Sample Device Selected")
            return False
        sample_device = DeviceManager.get_device(criteria.sample_device)

        # Get the columns for this report
        columns = self.table.get_columns(synthetic=False)

        sortcol = None
        if self.table.sortcol is not None:
            sortcol = self.table.sortcol.name

        # Time selection is available via criterai.starttime and endtime.
        # These are both datetime objects.
        t0 = criteria.starttime
        t1 = criteria.endtime

        # Time resolution is a timedelta object
        resolution = criteria.resolution

        # Grab the custom min and max criteria
        cmin = float(criteria.min)
        cmax = float(criteria.max)

        # Grab the table options
        beta = self.table.options.beta

        # Now, do some computation -- create table with a 'time' column
        # ranging from t0 to t1 with the defined resolution.  Then
        # for each additional column do some math function on the
        # data

        t = t0
        rows = []
        while t < t1:
            row = []
            for col in columns:
                if col.name == 'time':
                    row.append(t)
                else:
                    period_td = parse_timedelta(col.options.period)
                    period_secs = timedelta_total_seconds(period_td)
                    alpha = col.options.alpha
                    funcname = col.options.func

                    # seconds since the t0
                    secs = timedelta_total_seconds(t - t0)
                    rad = (secs / period_secs) * 2 * math.pi

                    funcmap = {
                        'sin': math.sin,
                        'cos': math.cos,
                        }

                    # Compute!
                    val = beta + alpha * funcmap[funcname](rad)

                    # Clip by the min/max criteria
                    val = max(cmin, val)
                    val = min(cmax, val)

                    # Add the value to the row
                    row.append(val)

            # Add the row
            rows.append(row)

            # This function runs pretty fast, but this shows how to mark
            # progress
            self.job.mark_progress(100 * (timedelta_total_seconds(t-t0) /
                                          timedelta_total_seconds(t1-t0)))
            t = t + resolution

        # Save the result in self.data
        self.data = rows
        if self.table.rows > 0:
            self.data = self.data[:self.table.rows]

        logger.info("Report %s returned %s rows" % (self.job, len(self.data)))
        return True
