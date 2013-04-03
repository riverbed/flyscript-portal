# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import math

from rvbd.common import timeutils

from libs.nicescale import NiceScale
from apps.report.models import Axes, Widget

class TableWidget:
    @classmethod
    def create(cls, report, table, title, width=6, rows=1000, height=300):
        w = Widget(report=report, title=title, rows=rows, width=width,
                   module=__name__, uiwidget=cls.__name__,
                   uioptions={'minHeight' : height})
        w.compute_row_col()
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, data):
        qcols = []
        columns = []

        for wc in widget.table().get_columns():
            qcols.append(wc.name)
            column = {'key': wc.name, 'label': wc.label, "sortable": True}
            if wc.datatype == 'bytes':
                column['formatter'] = 'formatBytes'
            elif wc.datatype == 'metric':
                column['formatter'] = 'formatMetric'

            columns.append(column)

        rows = []

        for reportrow in data:
            row = {}
            for i in range(0,len(qcols)):
                val = reportrow[i]
                row[qcols[i]] = val
                i = i + 1

            rows.append(row)

        data = {
            "chartTitle": widget.title,
            "columns" : columns,
            "data": rows
            }

        return data

class PieWidget:
    @classmethod
    def create(cls, report, table, title, width=6, rows=10, height=300):
        w = Widget(report=report, title=title, rows=rows, width=width,
                   module=__name__, uiwidget=cls.__name__,
                   uioptions={'minHeight' : height})
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey == True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))

        if table.sortcol is None:
            raise ValueError("Table %s does not have a sort column defined" % str(table))
            
        w.options = { 'key' : keycols[0],
                      'value': table.sortcol.name }
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, data):
        columns = widget.table().get_columns()

        catcol = [c for c in columns if c.name == widget.get_option('key')][0]
        col = [c for c in columns if c.name == widget.get_option('value')][0]

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
            for reportrow in data:
                row = {}
                for i in range(0,len(qcols)):
                    val = reportrow[i]
                    row[qcols[i]] = val
                    i = i + 1
                rows.append(row)
        else:
            # create a "full" pie to show something
            rows = [{qcols[0]: 1,
                     qcols[1]: 1}]

        data = {
            "chartTitle": widget.title,
            "type" : "pie",
            "categoryKey": catcol.name,
            "dataProvider": rows,
            "seriesCollection" : series,
            "legend" : { "position" : "right" }
            }

        return data


class TimeSeriesWidget:
    @classmethod
    def create(cls, report, table, title, width=6, height=300):
        w = Widget(report=report, title=title, width=width,
                   module=__name__, uiwidget=cls.__name__,
                   uioptions={'minHeight' : height})
        w.compute_row_col()
        timecols = [col.name for col in table.get_columns() if col.name == 'time']
        if len(timecols) == 0:
            raise ValueError("Table %s must have a 'time' column for a timeseries widget" % str(table))
        cols = [col.name for col in table.get_columns() if col.iskey == False]
        w.options={'axes': {'0': {'title': 'bytes/s',
                                  'position': 'left',
                                  'columns': cols}}
                   }
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, data):
        series = []
        qcols = ["time"]
        qcol_axis = [ -1]
        w_axes = Axes(widget.get_option('axes', None))

        axes = { "time" : { "keys" : ["time"],
                            "position": "bottom",
                            "type": "time",
                            "labelFormat": "%k:%M",
                            "styles" : { "label": { "fontSize": "8pt" }}}}

        for wc in widget.table().get_columns():
            # XXXCJ should not use name, maybe use datatype?
            if wc.name == 'time':
                continue

            series.append({"xKey": "time",
                           "xDisplayName": "Time",
                           "yKey": wc.name,
                           "yDisplayName": wc.label,
                           "styles": { "line": { "weight" : 1 },
                                       "marker": { "height": 3,
                                                   "width": 3 }}})
            qcols.append(wc.name)
            wc_axis = w_axes.getaxis(wc.name)
            qcol_axis.append(wc_axis)
            axis_name = 'axis'+str(wc_axis)
            if axis_name not in axes:
                axes[axis_name] = {"type": "numeric",
                                   "position" : w_axes.position(wc_axis),
                                   "keys": []
                                   }

            axes[axis_name]['keys'].append(wc.name)

        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        stacked = False # XXXCJ
        for reportrow in data:
            t0 = reportrow[0]
            try:
                t = timeutils.datetime_to_microseconds(t0) / 1000
            except AttributeError:
                t = t0 * 1000

            row = {'time': t}
            rowmin = {}
            rowmax = {}
            for i in range(1,len(qcols)):
                a = qcol_axis[i]
                val = reportrow[i]
                row[qcols[i]] = val if val != '' else None
                if a not in rowmin:
                    rowmin[a] = val if val != '' else 0
                    rowmax[a] = val if val != '' else 0
                else:
                    rowmin[a] = (rowmin[a] + val) if stacked else min(rowmin[a], val)
                    rowmax[a] = (rowmax[a] + val) if stacked else max(rowmax[a], val)

                i = i + 1

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a], rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a], rowmax[a])


            rows.append(row)

        for wc in widget.table().get_columns():
            wc_axis = w_axes.getaxis(wc.name)
            axis_name = 'axis'+str(wc_axis)

            if minval and maxval:
                n = NiceScale(minval[wc_axis], maxval[wc_axis])

                axes[axis_name]['minimum'] = "%.10f" % n.niceMin
                axes[axis_name]['maximum'] = "%.10f" % n.niceMax
                axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
                axes[axis_name]['styles'] = { 'majorUnit' : {'count' : n.numTicks } }
            else:
                # empty data which would result in keyError above
                axes[axis_name]['minimum'] = "0"
                axes[axis_name]['maximum'] = "1"
                axes[axis_name]['tickExponent'] = 1
                axes[axis_name]['styles'] = { 'majorUnit' : {'count' : 1 } }

            if wc.datatype == 'bytes':
                axes[axis_name]['formatter'] = 'formatBytes'
            elif wc.datatype == 'metric':
                axes[axis_name]['formatter'] = 'formatMetric'

        data = {
            "chartTitle": widget.title,
            "type" : "combo", # XXXCJ if stacked else "combo",
            "stacked" : stacked,
            "dataProvider": rows,
            "seriesCollection" : series,
            "axes": axes,
            "legend" : { "position" : "bottom",
                         "fontSize" : "8pt",
                         "styles" : { "gap": 0 } }
            }

        return data


class BarWidget:
    @classmethod
    def create(cls, report, table, title, width=6, rows=10, height=300):
        w = Widget(report=report, title=title, rows=rows, width=width,
                   module=__name__, uiwidget=cls.__name__,
                   uioptions={'minHeight' : height})
        w.compute_row_col()
        keycols = [col.name for col in table.get_columns() if col.iskey == True]
        if len(keycols) == 0:
            raise ValueError("Table %s does not have any key columns defined" % str(table))
            
        valuecols = [col.name for col in table.get_columns() if col.iskey == False]
        w.options = { 'key' : keycols[0],
                      'values': valuecols }
        w.save()
        w.tables.add(table)

    @classmethod
    def process(cls, widget, data):
        columns = widget.table().get_columns()

        catcol = [c for c in columns if c.name == widget.get_option('key')][0]
        cols = [c for c in columns if c.name in widget.get_option('values')]

        w_axes = Axes(widget.get_option('axes', None))

        series = []
        qcols = [catcol.name]
        qcol_axis = [ -1]
        axes = { catcol.name : { "keys" : [catcol.name],
                                     "position": "bottom",
                                     "styles" : { "label": { "rotation": -60 }}}}

        for wc in cols:
            series.append({"xKey": catcol.name,
                           "xDisplayName": "Time",
                           "yKey": wc.name,
                           "yDisplayName": wc.label,
                           "styles": { "line": { "weight" : 1 },
                                       "marker": { "height": 6,
                                                   "width": 20 }}})
            qcols.append(wc.name)
            wc_axis = w_axes.getaxis(wc.name)
            qcol_axis.append(wc_axis)
            axis_name = 'axis'+str(wc_axis)
            if axis_name not in axes:
                axes[axis_name] = {"type": "numeric",
                                   "position" : "left" if (wc_axis == 0) else "right",
                                   "keys": [] }

            axes[axis_name]['keys'].append(wc.name)

        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        stacked = False # XXXCJ
        for reportrow in data:
            row = {}
            rowmin = {}
            rowmax = {}
            for i in range(0,len(qcols)):
                a = qcol_axis[i]
                val = reportrow[i]
                row[qcols[i]] = val
                if a not in rowmin:
                    rowmin[a] = val
                    rowmax[a] = val
                else:
                    rowmin[a] = (rowmin[a] + val) if stacked else min(rowmin[a], val)
                    rowmax[a] = (rowmax[a] + val) if stacked else max(rowmax[a], val)

                i = i + 1

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a], rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a], rowmax[a])

            rows.append(row)

        for wc in cols:
            wc_axis = w_axes.getaxis(wc.name)
            axis_name = 'axis'+str(wc_axis)

            if minval and maxval:
                n = NiceScale(minval[wc_axis], maxval[wc_axis])

                axes[axis_name]['minimum'] = "%.10f" % n.niceMin
                axes[axis_name]['maximum'] = "%.10f" % n.niceMax
                axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
                axes[axis_name]['styles'] = { 'majorUnit' : {'count' : n.numTicks } }
            else:
                # empty data which would result in keyError above
                axes[axis_name]['minimum'] = "0"
                axes[axis_name]['maximum'] = "1"
                axes[axis_name]['tickExponent'] = 1
                axes[axis_name]['styles'] = { 'majorUnit' : {'count' : 1 } }


        data = {
            "chartTitle": widget.title,
            "type" : "column",
            "categoryKey": catcol.name,
            "dataProvider": rows,
            "seriesCollection" : series,
            "axes": axes
            }

        return data
