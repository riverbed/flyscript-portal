/**
 # Copyright (c) 2013 Riverbed Technology, Inc.
 #
 # This software is licensed under the terms and conditions of the
 # MIT License set forth at:
 #   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
 # This software is distributed "AS IS" as set forth in the License.
 */

var rvbd_maps = {};

rvbd_maps.MapWidget = function (dataurl, divid, options, criteria) {
    Widget.apply(this, [dataurl, divid, options, criteria]);
};
rvbd_maps.MapWidget.prototype = inherit(Widget.prototype)
rvbd_maps.MapWidget.prototype.constructor = rvbd_maps.MapWidget;

rvbd_maps.MapWidget.prototype.render = function(data)
{
    var contentid = this.divid + "_content";
    $('#' + this.divid).
        html('').
        append('<div id="' + contentid + '-title" class="widget-title">' + data['chartTitle'] + '</div>').
        append('<div id="' + contentid + '" class="mapcanvas"></div>')

    var div= $('#' + this.divid)
    
    $('#' + contentid + '-title')
        .height(20)
        .css({"text-align": "center"});

    $('#' + contentid).
        css({"margin": 10}).
        width(div.width()-22).
        height(div.height()-42)

    var map;

 // Ignore options here due to bug:
 // https://github.com/Leaflet/Leaflet/issues/2071
    var mapOptions = {
 //       center: [42.3583, -71.063],
 //       zoom: 3,
    };
    map = new L.map(document.getElementById(contentid),
                    mapOptions);

    L.tileLayer('http://{s}.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpg', {
        subdomains: ['otile1', 'otile2', 'otile3', 'otile4'],
        attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Tiles Courtesy of <a href="http://www.mapquest.com/" target="_blank">MapQuest</a> <img src="http://developer.mapquest.com/content/osm/mq_logo.png">',        
    }).addTo(map);

    if (data.minbounds) {
        bounds = new L.LatLngBounds(
            data.minbounds[0],
            data.minbounds[1]
        );
    } else {
        bounds = new L.LatLngBounds();
    }

    $.each(data.circles, function(i,c) {
        c.center = [c.center[0], c.center[1]];
        bounds.extend(c.center)

        var valstr = (c.formatter ?
                      Widget.prototype[c.formatter].call(undefined, c.value, 2) :
                      c.value) + c.units;

        var title = c.title + '\n' + valstr;

        var marker = L.marker(c.center, {
            title: title,
            icon: L.divIcon({
                className: 'circleMarker',
                iconSize: [c.radius * 2, c.radius * 2]
            })
        }).addTo(map);
    });
    bounds = bounds.pad(0.10);
    map.fitBounds(bounds);
}


