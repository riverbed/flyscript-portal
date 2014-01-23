# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import math
import datetime
import logging

from rvbd.common import timeutils
from rvbd.common.jsondict import JsonDict

from rvbd_portal.libs.nicescale import NiceScale
from rvbd_portal.apps.report.models import Axes, Widget

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
        qcols = []
        columns = []

        for wc in widget.table().get_columns():
            qcols.append(wc.name)
            column = {'key': wc.name, 'label': wc.label, "sortable": True}
            if wc.datatype == 'bytes':
                column['formatter'] = 'formatBytes'
            elif wc.datatype == 'metric':
                column['formatter'] = 'formatMetric'
            elif wc.datatype == 'time':
                column['formatter'] = 'formatTime'
            elif wc.datatype == 'pct':
                column['formatter'] = 'formatPct'
            elif wc.datatype == 'html':
                column['allowHTML'] = True
            columns.append(column)

        rows = []

        for rawrow in data:
            row = {}
            for i in range(0, len(qcols)):
                if qcols[i] == 'time':
                    t = rawrow[i]
                    try:
                        val = timeutils.datetime_to_microseconds(t) / 1000
                    except AttributeError:
                        val = t * 1000
                else:
                    val = rawrow[i]
                    
                row[qcols[i]] = val
                i = i + 1

            rows.append(row)

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "columns": columns,
            "data": rows
        }

        return data


class PieWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300):
        w = Widget(section=section, title=title, rows=rows, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))

        if table.sortcol is None:
            raise ValueError("Table %s does not have a sort column defined" % str(table))

        w.options = JsonDict(key=keycols[0],
                             value=table.sortcol.name)
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        columns = widget.table().get_columns()

        catcol = [c for c in columns if c.name == widget.options.key][0]
        col = [c for c in columns if c.name == widget.options.value][0]

        qcols = [catcol.name]
        qcols.append(col.name)

        series = []
        series.append({"categoryKey": catcol.name,
                       "categoryDisplayName": catcol.label,
                       "valueKey": col.name,
                       "valueDisplayName": col.label
                       })

        rows = []

        if len(data) > 0:
            for rawrow in data:
                row = {}
                for i in range(0, len(qcols)):
                    val = rawrow[i]
                    row[qcols[i]] = val
                    i = i + 1
                rows.append(row)
        else:
            # create a "full" pie to show something
            rows = [{qcols[0]: 1,
                     qcols[1]: 1}]

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
        timecols = [col.name for col in table.get_columns() if col.datatype == 'time']
        if len(timecols) == 0:
            raise ValueError("Table %s must have a datatype 'time' column for a timeseries widget" %
                             str(table))
        cols = cols or [col.name for col in table.get_columns() if col.datatype != 'time']
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
                self.dataindex = dataindex
                self.axis = axis
                self.istime = istime

        t_cols = widget.table().get_columns()
        colinfo = {}

        if widget.options.columns == '*':
            valuecolnames = [col.name for col in t_cols if col.datatype != 'time']
        else:
            valuecolnames = widget.options.columns
        # Retrieve the desired value columns
        # ...and the indices for the value values (as the 'data' has *all* columns)
        for i, c in enumerate(t_cols):
            if c.datatype == 'time':
                colinfo['time'] = ColInfo(c, i, -1, istime=(c.datatype == 'time'))
            elif c.name in valuecolnames:
                colinfo[c.name] = ColInfo(c, i, -1, istime=(c.datatype == 'time'))

        series = []
        w_axes = Axes(widget.options.axes)

        # Setup the time axis
        axes = {"time": {"keys": ["time"],
                         "position": "bottom",
                         "type": "time",
                         "styles": {"label": {"fontSize": "8pt", "rotation": "-45"}}}}

        # Create a better time format depending on t0/t1
        t_dataindex = colinfo['time'].dataindex

        #print ("t_dataindex: %d, data[0]: %s, data[1]: %s" % (t_dataindex, str(data[0]), str(data[1])))
        t0 = data[0][t_dataindex]
        t1 = data[-1][t_dataindex]
        if not hasattr(t0, 'utcfromtimestamp'):
            t0 = datetime.datetime.fromtimestamp(t0)
            t1 = datetime.datetime.fromtimestamp(t1)

        if (t1 - t0).seconds < 2:
            axes['time']['formatter'] = 'formatTimeMs'
        elif (t1 - t0).seconds < 120:
            axes['time']['labelFormat'] = '%k:%M:%S'
        else:
            axes['time']['labelFormat'] = '%k:%M'

        # Setup the other axes, checking the axis for each column
        for colname in valuecolnames:
            # Need to interate the valuecolnames array to preserve order
            ci = colinfo[colname]

            series.append({"xKey": "time",
                           "xDisplayName": "Time",
                           "yKey": ci.col.name,
                           "yDisplayName": ci.col.label,
                           "styles": {"line": {"weight": 1},
                                      "marker": {"height": 3,
                                                 "width": 3}}})

            ci.axis = w_axes.getaxis(ci.col.name)
            axis_name = 'axis' + str(ci.axis)
            if axis_name not in axes:
                axes[axis_name] = {"type": "numeric",
                                   "position": w_axes.position(ci.axis),
                                   "keys": []
                                   }

            axes[axis_name]['keys'].append(ci.col.name)

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
                row[ci.col.name] = val if val != '' else None

                if a not in rowmin:
                    rowmin[a] = val if val != '' else 0
                    rowmax[a] = val if val != '' else 0
                else:
                    rowmin[a] = (rowmin[a] + val) if stacked else min(rowmin[a], val)
                    rowmax[a] = (rowmax[a] + val) if stacked else max(rowmax[a], val)

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a], rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a], rowmax[a])

            rows.append(row)

        # Setup the scale values for the axes
        for ci in colinfo.values():
            if ci.istime:
                continue

            axis_name = 'axis' + str(ci.axis)

            if minval and maxval:
                n = NiceScale(minval[ci.axis], maxval[ci.axis])

                axes[axis_name]['minimum'] = "%.10f" % n.niceMin
                axes[axis_name]['maximum'] = "%.10f" % n.niceMax
                axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
                axes[axis_name]['styles'] = {'majorUnit': {'count': n.numTicks}}
            else:
                # empty data which would result in keyError above
                axes[axis_name]['minimum'] = "0"
                axes[axis_name]['maximum'] = "1"
                axes[axis_name]['tickExponent'] = 1
                axes[axis_name]['styles'] = {'majorUnit': {'count': 1}}

            if ci.col.datatype == 'bytes':
                axes[axis_name]['formatter'] = 'formatBytes'
            elif ci.col.datatype == 'metric':
                axes[axis_name]['formatter'] = 'formatMetric'

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": "area" if stacked else "combo",
            "stacked": stacked,
            "dataProvider": rows,
            "seriesCollection": series,
            "axes": axes,
            "legend": {"position": "bottom",
                       "fontSize": "8pt",
                       "styles": {"gap": 0}},
            "interactionType": "planar" if stacked else "marker"
        }

        #logger.debug("data:\n\n%s\n" % data)
        return data


class BarWidget(object):
    @classmethod
    def create(cls, section, table, title, width=6, rows=10, height=300, keycols=None, valuecols=None):
        w = Widget(section=section, title=title, rows=rows, width=width, height=height,
                   module=__name__, uiwidget=cls.__name__)
        w.compute_row_col()
        if keycols is None:
            keycols = [col.name for col in table.get_columns() if col.iskey is True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))

        if valuecols is None:
            valuecols = [col.name for col in table.get_columns() if col.iskey is False]
        w.options = JsonDict(dict={'keycols': keycols,
                                   'columns': valuecols,
                                   'axes': None})
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, job, data):
        class ColInfo:
            def __init__(self, col, dataindex, axis):
                self.col = col
                self.dataindex = dataindex
                self.axis = axis

        all_cols = widget.table().get_columns()

        # The category "key" column -- this is the column shown along the bottom of the bar widget
        keycols = [c for c in all_cols if c.name in widget.options.keycols]

        # The value columns - one set of bars for each
        cols = [c for c in all_cols if c.name in widget.options.columns]

        w_axes = Axes(widget.options.axes)

        # Array of data series definitions yui3 style
        series = []

        # Array of axis definitions yui3 style
        catname = '-'.join([k.name for k in keycols])
        axes = {catname: {"keys": [catname],
                          "position": "bottom",
                          "styles": {"label": {"rotation": -60}}}}
        
        # Map of column info by column name
        colmap = {}

        # Add keycols to the colmap
        for i, c in enumerate(all_cols):
            if (c not in keycols):
                continue
            ci = ColInfo(c, i, w_axes.getaxis(c.name))
            colmap[c.name] = ci

        for i, c in enumerate(all_cols):
            # Rest of this is for data cols only
            if (c not in cols):
                continue

            ci = ColInfo(c, i, w_axes.getaxis(c.name))
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
            if axis_name not in axes:
                axes[axis_name] = {"type": "numeric",
                                   "position": "left" if (ci.axis == 0) else "right",
                                   "keys": []}

            axes[axis_name]['keys'].append(c.name)

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
                    rowmin[a] = (rowmin[a] + val) if stacked else min(rowmin[a], val)
                    rowmax[a] = (rowmax[a] + val) if stacked else max(rowmax[a], val)

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a], rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a], rowmax[a])
            rows.append(row)

        # Build up axes
        for c in colmap.values():
            if c.col.iskey:
                continue

            axis_name = 'axis' + str(c.axis)

            if minval and maxval:
                n = NiceScale(minval[c.axis], maxval[c.axis])

                axes[axis_name]['minimum'] = "%.10f" % n.niceMin
                axes[axis_name]['maximum'] = "%.10f" % n.niceMax
                axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
                axes[axis_name]['styles'] = {'majorUnit': {'count': n.numTicks}}
            else:
                # empty data which would result in keyError above
                axes[axis_name]['minimum'] = "0"
                axes[axis_name]['maximum'] = "1"
                axes[axis_name]['tickExponent'] = 1
                axes[axis_name]['styles'] = {'majorUnit': {'count': 1}}

        data = {
            "chartTitle": widget.title.format(**job.actual_criteria),
            "type": "column",
            "categoryKey": catname,
            "dataProvider": rows,
            "seriesCollection": series,
            "axes": axes
        }

        return data
