# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from report.models import *

def TableWidget(widget, data):
    qcols = []
    columns = []

    for wc in widget.datatable.datacolumn_set.all():
        qcols.append(wc.querycol)
        column = {'key': wc.querycol, 'label': wc.label, "sortable": True}
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

def PieWidget(widget, data):
    catcol = DataColumn.objects.get(datatable=widget.datatable, querycol=widget.get_option('key'))
    datacol = DataColumn.objects.get(datatable=widget.datatable, querycol=widget.get_option('value'))

    qcols = [catcol.querycol]
    qcols.append(datacol.querycol)

    series = []
    series.append({"categoryKey": catcol.querycol,
                   "valueKey": datacol.querycol})

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
        "type" : "pie",
        "categoryKey": catcol.querycol,
        "dataProvider": rows,
        "seriesCollection" : series,
        "legend" : { "position" : "right" }
        }

    return data


def TimeSeriesWidget(widget, data):
    series = []
    qcols = ["time"]
    qcol_axis = [ -1]
    w_axes = Axes(widget.get_option('axes', None))
    
    axes = { "time" : { "keys" : ["time"],
                        "position": "bottom",
                        "type": "time",
                        "labelFormat": "%l:%M %p",
                        "styles" : { "label": { "rotation": -60 }}}}

    for wc in widget.datatable.datacolumn_set.all():
        if wc.querycol == 'time':
            continue
        
        series.append({"xKey": "time",
                       "yKey": wc.querycol,
                       "styles": { "line": { "weight" : 1 },
                                   "marker": { "height": 6,
                                               "width": 6 }}})
        qcols.append(wc.querycol)
        wc_axis = w_axes.getaxis(wc.querycol)
        qcol_axis.append(wc_axis)
        axis_name = 'axis'+str(wc_axis)
        if axis_name not in axes:
            axes[axis_name] = {"type": "numeric",
                               "position" : w_axes.position(wc_axis),
                               "keys": []
                               }

        axes[axis_name]['keys'].append(wc.querycol)

    rows = []

    # min/max values by axis 0/1
    minval = {}
    maxval = {}

    stacked = False # XXXCJ
    for reportrow in data:
        row = {'time': reportrow[0] * 1000}
        rowmin = {}
        rowmax = {}
        for i in range(1,len(qcols)):
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

    for wc in widget.datatable.datacolumn_set.all():
        wc_axis = w_axes.getaxis(wc.querycol)
        axis_name = 'axis'+str(wc_axis)
        n = NiceScale(minval[wc_axis], maxval[wc_axis])

        axes[axis_name]['minimum'] = "%.10f" % n.niceMin
        axes[axis_name]['maximum'] = "%.10f" % n.niceMax
        axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
        axes[axis_name]['styles'] = { 'majorUnit' : {'count' : n.numTicks } }
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
        "axes": axes
        }

    return data


def BarWidget(widget, data):
    catcol = DataColumn.objects.get(datatable=widget.datatable, querycol=widget.get_option('key'))
    datacols = []
    for v in widget.get_option('values'):
        datacols.append(DataColumn.objects.get(datatable=widget.datatable, querycol=v))

    w_axes = Axes(widget.get_option('axes', None))

    series = []
    qcols = [catcol.querycol]
    qcol_axis = [ -1]
    axes = { catcol.querycol : { "keys" : [catcol.querycol],
                                 "position": "bottom",
                                 "styles" : { "label": { "rotation": -60 }}}}

    for wc in datacols:
        series.append({"xKey": catcol.querycol,
                       "yKey": wc.querycol,
                       "styles": { "line": { "weight" : 1 },
                                   "marker": { "height": 6,
                                               "width": 20 }}})
        qcols.append(wc.querycol)
        wc_axis = w_axes.getaxis(wc.querycol)
        qcol_axis.append(wc_axis)
        axis_name = 'axis'+str(wc_axis)
        if axis_name not in axes:
            axes[axis_name] = {"type": "numeric",
                               "position" : "left" if (wc_axis == 0) else "right",
                               "keys": [] }

        axes[axis_name]['keys'].append(wc.querycol)

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

    for wc in datacols:
        wc_axis = w_axes.getaxis(wc.querycol)
        axis_name = 'axis'+str(wc_axis)
        n = NiceScale(minval[wc_axis], maxval[wc_axis])

        axes[axis_name]['minimum'] = "%.10f" % n.niceMin
        axes[axis_name]['maximum'] = "%.10f" % n.niceMax
        axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
        axes[axis_name]['styles'] = { 'majorUnit' : {'count' : n.numTicks } }

    data = {
        "chartTitle": widget.title,
        "type" : "column",
        "categoryKey": catcol.querycol,
        "dataProvider": rows,
        "seriesCollection" : series,
        "axes": axes
        }

    return data
