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
        .css({"text-align" : "center"});

    $('#' + contentid).
        css({"margin": 10}).
        width(div.width()-22).
        height(div.height()-42)

    var map;

    var mapOptions = {
        zoom: 3,
        center: new google.maps.LatLng(42.3583, -71.063),
        mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    bounds = new google.maps.LatLngBounds();
    map = new google.maps.Map(document.getElementById(contentid),
                              mapOptions);

    if (data.minbounds) {
        bounds = new google.maps.LatLngBounds(
            new google.maps.LatLng(data.minbounds[0][0], data.minbounds[0][1]),
            new google.maps.LatLng(data.minbounds[1][0], data.minbounds[1][1])
        );
    } else {
        bounds = new google.maps.LatLngBounds();
    }

    $.each(data.circles, function(i,c) {
        c.map = map;
        c.center = new google.maps.LatLng(c.center[0], c.center[1]);
        bounds.extend(c.center)

        var valstr = (c.formatter ?
                      Widget.prototype[c.formatter].call(undefined, c.value, 2) :
                      c.value) + c.units;

        var title = c.title + '\n' + valstr;


        var marker = new google.maps.Marker({
            position: c.center,
            map: map,
            title: title,
            icon: { path: google.maps.SymbolPath.CIRCLE,
                    scale: c.size,
                    strokeColor: "red",
                    strokeOpacity: 0.8,
                    strokeWeight: 0.5,
                    fillOpacity: 0.35,
                    fillColor: "red",
                  }
        });

        if (0) {
            circle = new google.maps.Circle(c);
            
            var infoWindow = new google.maps.InfoWindow();
            var html = c.label;
            
            google.maps.event.addListener(circle, 'click', function() {
                infoWindow.setContent(html);
                infoWindow.open(map, circle);
            });
        }
    });
    map.fitBounds(bounds);
}


