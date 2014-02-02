/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */

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
    $.each(widgets, function(w) { w.draw(); });
}

window.onresize = resize;

function Widget (posturl, divid, options, criteria) {
    this.posturl = posturl, 
    this.divid = divid;
    this.options = options;

    this.container = document.getElementById(divid);

    this.container.innerHTML = '<p>Loading...</p>';
    
    //debugger;
    if (options.height) {
        $('#' + divid).height(options.height);
    }
    $('#' + divid).showLoading();
    $('#' + divid).setLoading(0);
    var self = this;
    $.ajax({
        dataType: "json",
        type: "POST",
        url: self.posturl,
        data : { criteria: JSON.stringify(criteria) },
        success: function(data, textStatus) {
            self.joburl = data.joburl,
            setTimeout(function() { self.getData(criteria) }, 1000);
        },
        error: function(jqXHR, textStatus, errorThrown) { 
            $('#' + self.divid).hideLoading();
            var message = $("<div/>").html(textStatus + " : " + errorThrown).text()
            $('#' + self.divid).html("<p>Server error: <pre>" + message + "</pre></p>");
            rvbd_status[self.posturl] = 'error';
        }
    });
}

Widget.prototype.getData = function(criteria) {
    var self = this;
    $.ajax({
        dataType: "json",
        url: self.joburl, 
        data: null,
        success: function(data, textStatus) { 
            self.processResponse(criteria, data, textStatus); 
        },
        error: function(jqXHR, textStatus, errorThrown) { 
            $('#' + self.divid).hideLoading();
            var message = $("<div/>").html(textStatus + " : " + errorThrown).text()
            $('#' + self.divid).html("<p>Server error: <pre>" + message + "</pre></p>");
            rvbd_status[self.posturl] = 'error';
        }
    });
}

Widget.prototype.processResponse = function(criteria, response, textStatus)
{
    var self = this;
    if (response.status == 3) {
        // COMPLETE
        $('#' + this.divid).hideLoading();
        this.render(response.data);
        rvbd_status[self.posturl] = 'complete';
    } else if (response.status == 4) {
        // ERROR
        $('#' + this.divid).hideLoading();
        var message = $("<div/>").html(response.message).text()
        $('#' + this.divid).html("<p>Server error: <pre>" + message + "</pre></p>");
        rvbd_status[self.posturl] = 'error';
    } else {
        if (response.progress > 0) {
            $('#' + this.divid).setLoading(response.progress);
        }
        setTimeout(function() { self.getData(criteria) }, 1000);
    }
}

Widget.prototype.render = function(data)
{
    $('#' + this.divid).html(data);
}

function padzeros(n, p) {
    var pad = new Array(1 + p).join('0');
    return (pad + n).slice(-pad.length);
}

Widget.prototype.formatTimeMs = function(t, precision) {
    var d = new Date(t);
    return d.getHours() + 
        ':' + padzeros(d.getMinutes(),2) +
        ':' + padzeros(d.getSeconds(),2) +
        '.' + padzeros(d.getMilliseconds(),3);
    // return date.toString();
}

Widget.prototype.formatTime = function(t, precision) {
    var date = new Date(t);
    return date.toString();
}

Widget.prototype.formatBytes = function(bytes, precision) {
    if (bytes == undefined) return '';
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

Widget.prototype.formatPct = function(num, precision) {
    if (num == undefined) return '';
    if (num == 0) return '0';
    var v = num;
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
    return vs;
}

var rvbd_raw = {};

rvbd_raw.TableWidget = function (dataurl, divid, options, criteria) {
    Widget.apply(this, [dataurl, divid, options, criteria]);
};
rvbd_raw.TableWidget.prototype = inherit(Widget.prototype)
rvbd_raw.TableWidget.prototype.constructor = rvbd_raw.TableWidget;

rvbd_raw.TableWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<table id="' + contentid + '-table"></table>')

    var div= $('#' + this.divid)
    
    var table = $('#' + contentid + '-table')

    $.each(data, function(i,row) {
        rowstr = '<tr>'
        $.each(row, function(i,col) {
            rowstr = rowstr + '<td>' + col + '</td>';
        });
        rowstr = rowstr + '</tr>'
        table.append(rowstr);
        });
}

