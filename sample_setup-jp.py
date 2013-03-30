# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


# -*- coding: utf-8 -*-
from random import randint
import sys, os
import pickle
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.report.models import *

def make_data(widget, data):
    fname = "widget_data_%d_%d.cache" % (widget.report.id, widget.id)
    f = open(fname,"w")
    pickle.dump(data, f)
    f.close()

for cls in [WidgetColumn, Widget, Report, Device]:
    for o in cls.objects.all():
        o.delete()

profiler = Device(name="profiler",
                host = "cascade-pro1.nbttech.com",
                port = 443,
                username = "admin",
                password = "admin")
profiler.save()
   
main = Report(title="Main")
main.save()

#
w = TableWidget(report=main, device=profiler, duration=60, row=1, col=1, colwidth=6,
                title=u'全帯域 (最後時間)', groupby="por", rows=20)
w.save()

c = WidgetColumn(widget=w, name = 'port', label = 'ポート' )
c.save()
c = WidgetColumn(widget=w, name = 'protocol', label = 'プロトコル' )
c.save()
c = WidgetColumn(widget=w, name = 'protoport_name', label = '名前' )
c.save()
c = WidgetColumn(widget=w, name = 'avg_bytes', label = '秒当たりの平均バイト数', formatter="formatBytes" )
c.save()

w.sortcol = c
w.save()

c = WidgetColumn(widget=w, name = 'network_rtt', label = '往復時間', formatter="formatMetric" )
c.save()
c = WidgetColumn(widget=w, name = 'server_delay', label = 'サーバーの遅延', formatter="formatMetric" )
c.save()

make_data(w, [['8472', '17', 'vxlan-tunnel', 1362054.76782, '', ''],
              ['80', '6', 'http', 1051201.02989, 0.154, 0.23],
              ['1185', '6', 'catchpole', 681213.057471, 0.153, 0.004],
              ['7280', '6', 'itactionserver1', 646317.903448, 0.01, 0.004],
              ['445', '6', 'microsoft-ds', 496680.606897, 0.154, 0.005],
              ['443', '6', 'https', 438467.089655, 0.154, 0.593],
              ['9100', '6', 'jetdirect', 246713.90431, 0.154, 0.005],
              ['6881', '6', 'bittorrent', 164396.300287, 0.125, 0.004],
              ['3389', '6', 'ms-wbt-server', 157875.857471, 0.154, 0.005],
              ['2049', '6', 'nfs', 152608.86954, 0.156, 0.004],
              ['21', '6', 'ftp', 150349.28592, 0.155, 0.004],
              ['1521', '6', 'oracle', 95776.4637931, 0.011, 0.005],
              ['1433', '6', 'ms-sql-s', 94584.254023, 0.012, 0.005],
              ['1352', '6', 'lotusnote', 81479.1899425, 0.16, 0.903],
              ['389', '6', 'ldap', 52572.8350575, 0.014, 0.004],
              ['25', '6', 'smtp', 47319.891092, 0.118, 0.004],
              ['389', '17', 'ldap', 40373.633908, '', ''],
              ['5060', '17', 'sip', 15732.6597701, '', ''],
              ['161', '17', 'snmp', 9578.81350575, '', ''],
              ['53', '17', 'domain', 144.348563218, '', '']])

#
w = TimeSeriesWidget(report=main, device=profiler, duration=60, row=1, col=7, colwidth=6, title="往復時間 / サーバーの遅延", stacked=True)
w.save()

c = WidgetColumn(widget=w, name = 'network_rtt', label = '往復時間', axis = 0 )
c.save()

c = WidgetColumn(widget=w, name = 'server_delay', label = 'サーバーの遅延', axis = 0 )
c.save()

data = []
for t in xrange(60):
    data.append([1361757240 + 60*t, randint(90,130)/1000.0, randint(3, 20)/1000.0])
    
make_data(w, data)
                  

#
w = ColumnWidget(report=main, device=profiler, duration=3600, resolution=60*15, row=2, col=1, colwidth=6,
              title="全帯域 (最後日)", groupby="por", rows=10)
w.save()

c = WidgetColumn(widget=w, name = 'port', label = 'ポート' )
c.save()
c = WidgetColumn(widget=w, name = 'avg_bytes', label = '秒当たりの平均バイト数', formatter="formatBytes"  )
c.save()
    
make_data(w, [['80', 12355],
              ['443', 23355],
              ['8080', 8355]])
          

#
w = PieWidget(report=main, device=profiler, duration=3600, resolution=60*15, row=2, col=7, colwidth=6,
              title="全帯域 (最後日)", groupby="por", rows=10)
w.save()

c = WidgetColumn(widget=w, name = 'port', label = 'ポート' )
c.save()
c = WidgetColumn(widget=w, name = 'avg_bytes', label = '秒当たりの平均バイト数', formatter="formatBytes"  )
c.save()
    
make_data(w, [['80', 12355],
              ['443', 23355],
              ['8080', 8355]])
          

#
w = TimeSeriesWidget(report=main, device=profiler, duration=60, row=3, col=1, colwidth=12, title="秒当たりの平均バイト数 / 往復時間")
w.save()

c = WidgetColumn(widget=w, name = 'avg_bytes', label = '秒当たりの平均バイト数', axis = 0, formatter="formatBytes"  )
c.save()

c = WidgetColumn(widget=w, name = 'response_time', label = '往復時間', axis = 1 )
c.save()

c = WidgetColumn(widget=w, name = 'network_rtt', label = '往復時間', axis = 2)
c.save()

data = []
for t in xrange(60):
    rtt = randint(90, 130)/1000.0
    sd = randint(3, 20)/1000.0
    data.append([1361757240 + 60*t, randint(10000000, 20000000), rtt + sd, rtt])
    
make_data(w, data)
                  
# Another report
interfaces = Report(title="Interfaces")
interfaces.save()

#
w = TimeSeriesWidget(report=interfaces, device=profiler, duration=60, row=1, col=1, title="Overall Bandwidth")
w.save()

c = WidgetColumn(widget=w, name = 'avg_bytes', label = 'Avg Bytes/s', formatter="formatBytes"  )
c.save()


