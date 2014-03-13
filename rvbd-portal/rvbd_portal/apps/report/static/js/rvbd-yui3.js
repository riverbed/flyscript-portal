/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */

var rvbd_yui3 = {};

rvbd_yui3.TimeSeriesWidget = function (dataurl, divid, options, criteria) {
    Widget.apply(this, [dataurl, divid, options, criteria]);
}

rvbd_yui3.TimeSeriesWidget.prototype = inherit(Widget.prototype)
rvbd_yui3.TimeSeriesWidget.prototype.constructor = rvbd_yui3.TimeSeriesWidget;

rvbd_yui3.TimeSeriesWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title" class="widget-title">' + data['chartTitle'] + '</div>').
        append('<div id="' + contentid + '"></div>')

    var div= $('#' + this.divid)

    $('#' + contentid + '-title')
        .height(20)
        .css({"text-align" : "center"});

    $('#' + contentid).
        css({"margin": 10}).
        width(div.width()-22).
        height(div.height()-42)

    $.each(data.axes, function (i, axis) {
        if ("formatter" in axis) {
            axis.labelFunction = (function(formatter) {
                return function (v,fmt,tooltip) { return formatter.call(undefined, v, tooltip ? 2 : 1); }
            })(Widget.prototype[axis.formatter]);
        } else if ("tickExponent" in axis && axis.tickExponent < 0) {
            axis.labelFunction = (function (exp) {
                return function(v, fmt, tooltip) {
                    if (tooltip) {
                        return v.toFixed(3-exp);
                    } else {
                        return v.toFixed(1-exp);
                    }
                }
            })(axis.tickExponent);
        }
    });

    data.tooltip = {};
    data.tooltip.setTextFunction = function(textField, val) {
        textField.setHTML(val);
    };

    data.tooltip.markerLabelFunction =
        function(cat, val, idx, s, sidx) {
            var msg =
                cat.displayName + ": " +
                cat.axis.get("labelFunction").apply(this, [cat.value, cat.axis.get("labelFormat"), true]) + "<br>" +
                val.displayName + ": " +
                val.axis.get("labelFunction").apply(this, [val.value, val.axis.get("labelFormat"), true]);

            return msg;
        };

    data.render =  "#" + contentid
    YUI().use('charts-legend', function(Y) {
        var chart = new Y.Chart(data);
    });
}

rvbd_yui3.TableWidget = function (dataurl, divid, options, criteria) {
    Widget.apply(this, [dataurl, divid, options, criteria]);
};
rvbd_yui3.TableWidget.prototype = inherit(Widget.prototype)
rvbd_yui3.TableWidget.prototype.constructor = rvbd_yui3.TableWidget;

rvbd_yui3.TableWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title" class="widget-title">' + data['chartTitle'] + '</div>').
        append('<div class="yui3-skin-sam" id="' + contentid + '"></div>')

    var div= $('#' + this.divid)

    $('#' + contentid + '-title')
        .height(20)
        .css({"text-align" : "center"});

    $('#' + contentid).
        css({"margin": 10}).
        width(div.width()-22).
        height(div.height()-42)

    data.render =  "#" + contentid
    data.scrollable = 'xy';
    data.height = $('#' + contentid).height() + "px";
    data.width = $('#' + contentid).width() + "px";

    $.each(data.columns, function(i, c) {
        if (("formatter" in c) && (c.formatter in Widget.prototype)) {
            c.formatter = (function(key,f) {
                return function(v) {return f.call(undefined, v.data[key]); }
            })(c.key, Widget.prototype[c.formatter]);
        } else {
            delete c.formatter;
        }
    });

    YUI().use('datatable-scroll', 'datatable-sort', function(Y) {
        var table = new Y.DataTable(data);
    });
}


rvbd_yui3.ChartWidget = function (dataurl, divid, options, criteria) {
    Widget.apply(this, [dataurl, divid, options, criteria]);
}
rvbd_yui3.ChartWidget.prototype = inherit(Widget.prototype)
rvbd_yui3.ChartWidget.prototype.constructor = rvbd_yui3.ChartWidget;

rvbd_yui3.ChartWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title" class="widget-title">' + data['chartTitle'] + '</div>').
        append('<div id="' + contentid + '"></div>')

    var div= $('#' + this.divid)

    $('#' + contentid + '-title')
        .height(20)
        .css({"text-align" : "center"});

    $('#' + contentid).
        css({"margin": 10}).
        width(div.width()-22).
        height(div.height()-42)

    $.each([0,1], function (i, v) {
        var n = 'axis'+v;
        if (n in data.axes && data.axes[n].tickExponent < 0) {
            var axis = data.axes[n];
            axis.labelFunction = (function (exp) {
                return function(v, fmt, tooltip) {
                    if (tooltip) {
                        return v.toFixed(3-exp);
                    } else {
                        return v.toFixed(1-exp);
                    }
                }
            })(axis.tickExponent);
        }
    });

    data.tooltip = {};
    data.tooltip.setTextFunction = function(textField, val) {
        textField.setHTML(val);
    };

    data.tooltip.markerLabelFunction =
        function(cat, val, idx, s, sidx) {
            var msg =
                cat.displayName + ": " +
                cat.axis.get("labelFunction").apply(this, [cat.value, cat.axis.get("labelFormat"), true]) + "<br>" +
                val.displayName + ": " +
                val.axis.get("labelFunction").apply(this, [val.value, val.axis.get("labelFormat"), true]);

            return msg;
        };

    data.render =  "#" + contentid
    YUI().use('charts-legend', function(Y) {
        var chart = new Y.Chart(data);
    });
}

rvbd_yui3.PieWidget = function (dataurl, divid, options, criteria) {
    Widget.apply(this, [dataurl, divid, options, criteria]);
}
rvbd_yui3.PieWidget.prototype = inherit(Widget.prototype)
rvbd_yui3.PieWidget.prototype.constructor = rvbd_yui3.PieWidget;

rvbd_yui3.PieWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title" class="widget-title">' + data['chartTitle'] + '</div>').
        append('<div id="' + contentid + '"></div>')

    var div= $('#' + this.divid)

    $('#' + contentid + '-title')
        .height(20)
        .css({"text-align" : "center"});

    $('#' + contentid).
        css({"margin": 10}).
        width(div.width()-22).
        height(div.height()-42)

    data.render =  "#" + contentid
    YUI().use('charts-legend', function(Y) {
        var chart = new Y.Chart(data);
    });
}
