# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import re
import math
import datetime
import logging

from rvbd.common import timeutils
from rvbd.common.jsondict import JsonDict

from rvbd_portal.libs.nicescale import NiceScale
from rvbd_portal.apps.report.models import Axes, Widget

logger = logging.getLogger(__name__)


def cleankey(s):
    return re.sub('[:. ]', '_', s)


class TableWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=1000, height=300):
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        class ColInfo:
            def __init__(self, col, dataindex, istime=False):
                self.col = col
                self.key = cleankey(col.name)
                self.dataindex = dataindex
                self.istime = istime

        w_keys = []      # Widget column keys in order that matches data
        colinfo = {}     # Map of ColInfo by key
        w_columns = []   # Widget column definitions

        for i,wc in enumerate(job.get_columns()):
            ci = ColInfo(wc, i, wc.datatype == 'time')
            colinfo[ci.key] = ci
            w_keys.append(ci.key)
            w_column = {'key': ci.key, 'label': wc.label, "sortable": True}
            if wc.datatype == 'bytes':
                w_column['formatter'] = 'formatBytes'
            elif wc.datatype == 'metric':
                w_column['formatter'] = 'formatMetric'
            elif wc.datatype == 'time':
                w_column['formatter'] = 'formatTime'
            elif wc.datatype == 'pct':
                w_column['formatter'] = 'formatPct'
            elif wc.datatype == 'html':
                w_column['allowHTML'] = True
            w_columns.append(w_column)

        rows = []

        for rawrow in data:
            row = {}

            for i, key in enumerate(w_keys):
                if colinfo[key].istime:
                    t = rawrow[i]
                    try:
                        val = timeutils.datetime_to_microseconds(t) / 1000
                    except AttributeError:
                        val = t * 1000
                else:
                    val = rawrow[i]

                row[key] = val

            rows.append(row)

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "columns": w_columns,
            "data": rows
        }

        return data


class PieWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300):
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" %
                             str(table))

        if table.sortcol is None:
            raise ValueError("Table %s does not have a sort column defined" %
                             str(table))

        w.options = JsonDict(key=keycols[0],
                             value=table.sortcol.name)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        columns = job.get_columns()

        col_names = [c.name for c in columns]
        catcol = [c for c in columns if c.name == widget.options.key][0]
        col = [c for c in columns if c.name == widget.options.value][0]

        series = []
        series.append({"categoryKey": catcol.name,
                       "categoryDisplayName": catcol.label,
                       "valueKey": col.name,
                       "valueDisplayName": col.label
                       })

        rows = []

        if len(data) > 0:
            for rawrow in data:
                row = dict(zip(col_names, rawrow))
                r = {catcol.name: row[catcol.name],
                     col.name: row[col.name]}
                rows.append(r)
        else:
            # create a "full" pie to show something
            rows = [{catcol.name: 1,
                     col.name: 1}]

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": "pie",
            "categoryKey": catcol.name,
            "dataProvider": rows,
            "seriesCollection": series,
            "legend": {"position": "right"}
        }

        return data


class TimeSeriesWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, height=300,
               stacked=False, cols=None, altaxis=None):
        w = Widget(section=section, title=title, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        timecols = [col.name for col in table.get_columns()
                    if col.datatype == 'time']
        if len(timecols) == 0:
            raise ValueError("Table %s must have a datatype 'time' column for "
                             "a timeseries widget" % str(table))
        cols = cols or [col.name for col in table.get_columns()
                        if col.datatype != 'time']
        if altaxis:
            axes = {'0': {'position': 'left',
                          'columns': [col for col in cols if col not in altaxis]},
                    '1': {'position': 'right',
                          'columns': [col for col in cols if col in altaxis]}
                    }
        else:
            axes = {'0': {'position': 'left',
                          'columns': cols}}
        w.options = JsonDict(axes=axes,
                             columns=cols,
                             stacked=stacked)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):

        class ColInfo:
            def __init__(self, col, dataindex, axis, istime=False):
                self.col = col
                self.key = cleankey(col.name)
                self.dataindex = dataindex
                self.axis = axis
                self.istime = istime

        t_cols = job.get_columns()
        colinfo = {}   # map by widget key

        # columns of '*' is a special case, just use all
        # defined columns other than time
        if widget.options.columns == '*':
            valuecolnames = [col.name for col in t_cols
                             if col.datatype != 'time']
        else:
            valuecolnames = widget.options.columns

        # Column keys are the 'cleaned' column names
        w_keys = [cleankey(n) for n in valuecolnames]

        # Retrieve the desired value columns
        # ...and the indices for the value values
        # (as the 'data' has *all* columns)
        for i, c in enumerate(t_cols):
            if c.datatype == 'time':
                ci = ColInfo(c, i, -1, istime=True)
            elif c.name in valuecolnames:
                ci = ColInfo(c, i, -1, istime=False)
            colinfo[ci.key] = ci

        w_series = []
        axes = Axes(widget.options.axes)

        # Setup the time axis
        w_axes = {"time": {"keys": ["time"],
                           "position": "bottom",
                           "type": "time",
                           "styles": {"label": {"fontSize": "8pt",
                                                "rotation": "-45"}}}}

        # Create a better time format depending on t0/t1
        t_dataindex = colinfo['time'].dataindex

        t0 = data[0][t_dataindex]
        t1 = data[-1][t_dataindex]
        if not hasattr(t0, 'utcfromtimestamp'):
            t0 = datetime.datetime.fromtimestamp(t0)
            t1 = datetime.datetime.fromtimestamp(t1)

        if (t1 - t0).seconds < 2:
            w_axes['time']['formatter'] = 'formatTimeMs'
        elif (t1 - t0).seconds < 120:
            w_axes['time']['labelFormat'] = '%k:%M:%S'
        else:
            w_axes['time']['labelFormat'] = '%k:%M'

        # Setup the other axes, checking the axis for each column
        for w_key in w_keys:
            # Need to interate the valuecolnames array to preserve order
            ci = colinfo[w_key]

            w_series.append({"xKey": "time",
                             "xDisplayName": "Time",
                             "yKey": ci.key,
                             "yDisplayName": ci.col.label,
                             "styles": {"line": {"weight": 1},
                                        "marker": {"height": 3,
                                                   "width": 3}}})

            ci.axis = axes.getaxis(ci.col.name)
            axis_name = 'axis' + str(ci.axis)
            if axis_name not in w_axes:
                w_axes[axis_name] = {"type": "numeric",
                                     "position": axes.position(ci.axis),
                                     "keys": []
                                     }

            w_axes[axis_name]['keys'].append(ci.key)

        # Output row data
        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        stacked = widget.options.stacked
        # Iterate through all rows if input data
        for rawrow in data:
            t = rawrow[t_dataindex]
            try:
                t = timeutils.datetime_to_microseconds(t) / 1000
            except AttributeError:
                t = t * 1000

            row = {'time': t}
            rowmin = {}
            rowmax = {}
            for ci in colinfo.values():
                if ci.istime:
                    continue
                a = ci.axis
                val = rawrow[ci.dataindex]
                row[ci.key] = val if val != '' else None

                if a not in rowmin:
                    rowmin[a] = val if val != '' else 0
                    rowmax[a] = val if val != '' else 0
                else:
                    rowmin[a] = (rowmin[a] + val) if stacked else min(rowmin[a],
                                                                      val)
                    rowmax[a] = (rowmax[a] + val) if stacked else max(rowmax[a],
                                                                      val)

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a],
                                                                    rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a],
                                                                    rowmax[a])

            rows.append(row)

        # Setup the scale values for the axes
        for ci in colinfo.values():
            if ci.istime:
                continue

            axis_name = 'axis' + str(ci.axis)

            if minval and maxval:
                n = NiceScale(minval[ci.axis], maxval[ci.axis])

                w_axes[axis_name]['minimum'] = "%.10f" % n.niceMin
                w_axes[axis_name]['maximum'] = "%.10f" % n.niceMax
                w_axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
                w_axes[axis_name]['styles'] = {'majorUnit': {'count': n.numTicks}}
            else:
                # empty data which would result in keyError above
                w_axes[axis_name]['minimum'] = "0"
                w_axes[axis_name]['maximum'] = "1"
                w_axes[axis_name]['tickExponent'] = 1
                w_axes[axis_name]['styles'] = {'majorUnit': {'count': 1}}

            if ci.col.datatype == 'bytes':
                w_axes[axis_name]['formatter'] = 'formatBytes'
            elif ci.col.datatype == 'metric':
                w_axes[axis_name]['formatter'] = 'formatMetric'

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": "area" if stacked else "combo",
            "stacked": stacked,
            "dataProvider": rows,
            "seriesCollection": w_series,
            "axes": w_axes,
            "legend": {"position": "bottom",
                       "fontSize": "8pt",
                       "styles": {"gap": 0}},
            "interactionType": "planar" if stacked else "marker"
        }

        #logger.debug("data:\n\n%s\n" % data)
        return data


class ChartWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300,
               keycols=None, valuecols=None, chart_type='line'):
        w = Widget(section=section, title=title, rows=rows, width=width,
                   height=height, module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        if keycols is None:
            keycols = [col.name for col in table.get_columns()
                       if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" %
                             str(table))

        if valuecols is None:
            valuecols = [col.name for col in table.get_columns()
                         if col.iskey is False]
        w.options = JsonDict(dict={'keycols': keycols,
                                   'columns': valuecols,
                                   'axes': None,
                                   'chart_type': chart_type})
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        class ColInfo:
            def __init__(self, col, dataindex, axis):
                self.col = col
                self.dataindex = dataindex
                self.axis = axis

        all_cols = job.get_columns()

        # The category "key" column -- this is the column shown along the
        # bottom of the bar widget
        keycols = [c for c in all_cols if c.name in widget.options.keycols]

        # columns of '*' is a special case, just use all
        # defined columns other than time
        if widget.options.columns == '*':
            cols = [c for c in all_cols if not c.iskey]
        else:
            # The value columns - one set of bars for each
            cols = [c for c in all_cols if c.name in widget.options.columns]

        axes = Axes(widget.options.axes)

        # Array of data series definitions yui3 style
        series = []

        # Array of axis definitions yui3 style
        catname = '-'.join([k.name for k in keycols])
        w_axes = {catname: {"keys": [catname],
                            "position": "bottom",
                            "styles": {"label": {"rotation": -60}}}}

        # Map of column info by column name
        colmap = {}

        # Add keycols to the colmap
        for i, c in enumerate(all_cols):
            if c not in keycols:
                continue
            ci = ColInfo(c, i, axes.getaxis(c.name))
            colmap[c.name] = ci

        for i, c in enumerate(all_cols):
            # Rest of this is for data cols only
            if c not in cols:
                continue

            ci = ColInfo(c, i, axes.getaxis(c.name))
            colmap[c.name] = ci

            series.append({"xKey": '-'.join([k.name for k in keycols]),
                           "xDisplayName": ','.join([k.label for k in keycols]),
                           "yKey": c.name,
                           "yDisplayName": c.label,
                           "styles": {"line": {"weight": 1},
                                      "marker": {"height": 6,
                                                 "width": 20}}})


            # The rest compute axis min/max for datavalues, so skip keys
            if c.iskey:
                continue

            axis_name = 'axis' + str(ci.axis)
            if axis_name not in w_axes:
                w_axes[axis_name] = {"type": "numeric",
                                     "position": ("left" if (ci.axis == 0)
                                                  else "right"),
                                     "keys": []}

            w_axes[axis_name]['keys'].append(c.name)

        # Array of actual data yui3 style.  Each row is a dict of key->value
        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        stacked = False  # XXXCJ

        for rawrow in data:
            row = {}
            rowmin = {}
            rowmax = {}

            # collect key values
            keyvals = []
            for c in colmap.values():
                if not c.col.iskey:
                    continue
                keyvals.append(rawrow[c.dataindex])
            row[catname] = ','.join(keyvals)

            # collect the data values
            for c in colmap.values():
                #
                if c.col.iskey:
                    continue

                # Set the value
                val = rawrow[c.dataindex]
                row[c.col.name] = val


                a = c.axis
                if c.axis not in rowmin:
                    rowmin[a] = val
                    rowmax[a] = val
                else:
                    rowmin[a] = (rowmin[a] + val) if stacked else min(rowmin[a],
                                                                      val)
                    rowmax[a] = (rowmax[a] + val) if stacked else max(rowmax[a],
                                                                      val)

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a],
                                                                    rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a],
                                                                    rowmax[a])
            rows.append(row)

        # Build up axes
        for c in colmap.values():
            if c.col.iskey:
                continue

            axis_name = 'axis' + str(c.axis)

            if minval and maxval:
                n = NiceScale(minval[c.axis], maxval[c.axis])

                w_axes[axis_name]['minimum'] = "%.10f" % n.niceMin
                w_axes[axis_name]['maximum'] = "%.10f" % n.niceMax
                w_axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
                w_axes[axis_name]['styles'] = {'majorUnit': {'count': n.numTicks}}
            else:
                # empty data which would result in keyError above
                w_axes[axis_name]['minimum'] = "0"
                w_axes[axis_name]['maximum'] = "1"
                w_axes[axis_name]['tickExponent'] = 1
                w_axes[axis_name]['styles'] = {'majorUnit': {'count': 1}}

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": widget.options.chart_type,
            "categoryKey": catname,
            "dataProvider": rows,
            "seriesCollection": series,
            "axes": w_axes,
            "legend": {"position": "bottom",
                       "fontSize": "8pt",
                       "styles": {"gap": 0}}
        }

        return data

class BarWidget(ChartWidget):
    @classmethod
    def create(cls, *args, **kwargs):
        kwargs['rows'] = kwargs.get('rows', 10)
        return ChartWidget.create(*args, chart_type='column', **kwargs)

class LineWidget(ChartWidget):
    @classmethod
    def create(cls, *args, **kwargs):
        kwargs['rows'] = kwargs.get('rows', 0)
        return ChartWidget.create(*args, chart_type='line', **kwargs)
