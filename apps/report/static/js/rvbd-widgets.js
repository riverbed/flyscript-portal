/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
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
    widgets.forEach(function(w) { w.draw(); })
}

window.onresize = resize;

function Widget (dataurl, divid, options, ts) {
    this.dataurl = dataurl
    this.divid = divid;
    this.options = options;

    this.container = document.getElementById(divid);

    this.container.innerHTML = '<p>Loading...</p>';
    
    if (options.minHeight) {
        $('#' + divid).height(options.minHeight);
    }
    $('#' + divid).showLoading();
    $('#' + divid).setLoading(0);
    var self = this;
    setTimeout(function() { self.getData(ts || $.now()) }, 0);
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
        $('#' + this.divid).html("<p>Server error: <pre>" + response.message + "</pre></p>");
    } else {
        if (response.progress > 0) {
            $('#' + this.divid).setLoading(response.progress);
        }
        setTimeout(function() { self.getData(ts) }, 1000);
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
