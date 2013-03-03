function inherit(p) {
    if (p == null) throw TypeError();
    if (Object.create)
        return Object.create(p);
    var t = typeof p;
    if (t !== "object" && t !== "function") throw TypeError();
    function f() {};
    f.prototype = p;
    return new f();
}

var widgets = [];

function resize() {
    widgets.forEach(function(w) { w.draw(); })
}

window.onresize = resize;

function Widget (dataurl, divid, options) {
    this.dataurl = dataurl
    this.divid = divid;
    this.options = options;

    this.container = document.getElementById(divid);

    this.container.innerHTML = '<p>Loading...</p>';
    
    if (options.minHeight) {
        $('#' + divid).height(options.minHeight);
    }
    $('#' + divid).showLoading();
    var self = this;
    setTimeout(function() { self.getData($.now()) }, 0);
}

Widget.prototype.getData = function(ts) {
    var self = this;
    $.ajax({
        dataType: "json",
        url: this.dataurl + "?ts=" + ts,
        data: null,
        success: function(data, textStatus) { self.processResponse(ts, data, textStatus); },
        error: function(jqXHR, textStatus, errorThrown) { alert("an error occured: " + textStatus + " : " + errorThrown); }
    });
}

Widget.prototype.processResponse = function(ts, response, textStatus)
{
    var self = this;
    if (response.status == 2) {
        // COMPLETE
        $('#' + this.divid).hideLoading();
        this.render(response.data);
    } else if (response.status == 3) {
        // ERROR
        $('#' + this.divid).hideLoading();
        $('#' + this.divid).html("<p>Server error: " + response.message + "</p>");
    } else {
        setTimeout(function() { self.getData(ts) }, 500);
    }
}

Widget.prototype.render = function(data)
{
    $('#' + this.divid).html(data);
}

Widget.prototype.formatBytes = function(bytes, precision) {
    if (bytes == 0) return '0';
    var e = parseInt(Math.floor(Math.log(bytes) / Math.log(1000)));
    var v = (bytes / Math.pow(1000, e));
    var vs;
    if (precision != undefined) {
        vs = v.toFixed(precision);
    } else if (v < 10) {
        vs = v.toFixed(3);
    } else if (v < 100) {
        vs = v.toFixed(2);
    } else {
        vs = v.toFixed(1);
    }
    if (e >= 0) {
        return vs + ['', 'k', 'M', 'G', 'T'][e];
    } else {
        return vs + ['', 'm', 'u', 'n'][-e];
    }    
}

Widget.prototype.formatMetric = Widget.prototype.formatBytes;

function TimeSeriesWidget (dataurl, divid, options) {
    Widget.apply(this, [dataurl, divid, options]);
}
TimeSeriesWidget.prototype = inherit(Widget.prototype)
TimeSeriesWidget.prototype.constructor = TimeSeriesWidget;

TimeSeriesWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title">' + data['chartTitle'] + '</div>').
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
                return function (v,fmt,tooltip) { return formatter.call(undefined, v, tooltip ? 2 : 0); }
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
    YUI().use('charts', function(Y) {
        var chart = new Y.Chart(data);
    });
}

function TableWidget (dataurl, divid, options) {
    Widget.apply(this, [dataurl, divid, options]);
}
TableWidget.prototype = inherit(Widget.prototype)
TableWidget.prototype.constructor = TableWidget;

TableWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title">' + data['chartTitle'] + '</div>').
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


function ColumnWidget (dataurl, divid, options) {
    Widget.apply(this, [dataurl, divid, options]);
}
ColumnWidget.prototype = inherit(Widget.prototype)
ColumnWidget.prototype.constructor = ColumnWidget;

ColumnWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title">' + data['chartTitle'] + '</div>').
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
    YUI().use('charts', function(Y) {
        var chart = new Y.Chart(data);
    });
}

function PieWidget (dataurl, divid, options) {
    Widget.apply(this, [dataurl, divid, options]);
}
PieWidget.prototype = inherit(Widget.prototype)
PieWidget.prototype.constructor = PieWidget;

PieWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title">' + data['chartTitle'] + '</div>').
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
    YUI().use('charts', 'charts-legend', function(Y) {
        var chart = new Y.Chart(data);
    });
}

