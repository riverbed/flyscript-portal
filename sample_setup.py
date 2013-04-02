# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from random import randint
import sys, os
import pickle
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import *
from apps.report.models import *
from apps.geolocation.models import *
from apps.datasource.modules.shark import ColumnOptions as shark_ColumnOptions


#### Customize devices and authorization here

tm08 = Device(name="tm08-1",
              module="profiler",
              host="tm08-1.lab.nbttech.com",
              port=443,
              username="admin",
              password="admin")
tm08.save()

v10 = Device(name="vdorothy10",
             module="shark",
             host="vdorothy10.lab.nbttech.com",
               port=443,
             username="admin",
             password="admin")
v10.save()

#### End device customization

Location(name="Seattle", address="10.99.11.0", mask="255.255.255.0", latitude=47.6097, longitude=-122.3331).save()
Location(name="LosAngeles", address="10.99.12.0", mask="255.255.255.0", latitude=34.0522, longitude=-118.2428).save()
Location(name="Phoenix", address="10.99.13.0", mask="255.255.255.0", latitude=33.43, longitude=-112.02).save()
Location(name="Columbus", address="10.99.14.0", mask="255.255.255.0", latitude=40.00, longitude=-82.88).save()
Location(name="SanFrancisco", address="10.99.15.0", mask="255.255.255.0", latitude=37.75, longitude=-122.68).save()
Location(name="Austin", address="10.99.16.0", mask="255.255.255.0", latitude=30.30, longitude=-97.70).save()
Location(name="Philadelphia", address="10.99.17.0", mask="255.255.255.0", latitude=39.88, longitude=-75.25).save()
Location(name="Hartford", address="10.99.18.0", mask="255.255.255.0", latitude=41.73, longitude=-72.65).save()
Location(name="DataCenter", address="10.100.0.0", mask="255.255.0.0", latitude=35.9139, longitude=-81.5392).save()

#
# Overall report
#

overall = Report(title="Overall")
overall.save()

# Define a TimeSeries 
dt = Table(name='ts1', module='profiler', device=tm08, duration=60, 
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
dt.save()
Column(table=dt, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

wid = Widget(report=overall, title="Overall Traffic", 
             row=1, col=1, colwidth=12,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']}
                               }},
             module="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a TimeSeries 
dt = Table(name='ts2', module='profiler', device=tm08, duration=60,
           filterexpr = 'host 10.99/16',
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
dt.save()
Column(table=dt, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

wid = Widget(report=overall, title="Traffic for hosts in 10.99/16", 
             row=2, col=1, colwidth=6,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']}
                               }},
             module="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a TimeSeries 
dt = Table(name='ts3', module='profiler', device=tm08, duration=60,
           filterexpr = 'host 10.99.15/24',
           options={'realm': 'traffic_overall_time_series',
                    'groupby': 'time'})
dt.save()
Column(table=dt, name='time', iskey=True, label='Time', datatype='time', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label='Avg Bytes/s', datatype='bytes', units = 'B/s', position=2).save()

wid = Widget(report=overall, title="Traffic for hosts in  10.99.15/24", 
             row=2, col=2, colwidth=6,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']}
                               }},
             module="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a Table
dt = Table(name='hg', module='profiler', device=tm08, duration=60,
               options={'groupby': 'host_group'})
dt.save()
Column(table=dt, name='group_name', iskey=True, label = 'Group Name', position=1).save()
c = Column(table=dt, name='total_bytes', iskey=False, label = 'Total Bytes', datatype='bytes', units='B', position=2)
c.save()
dt.sortcol = c
dt.save()

wid = Widget(report=overall, title="Locations by Bytes",  
             row=3, col=1, rows=10, colwidth=6, 
             options = {'key': 'group_name',
                        'value': 'total_bytes'},
             module="yui3", uiwidget="PieWidget",
             uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

# Define a Table
dt = Table(name='hg2', module='profiler', device=tm08, duration=60,
           options={'groupby': 'host_group'})
dt.save()
Column(table=dt, name='group_name', iskey=True, label = 'Group Name', position=1).save()
Column(table=dt, name='response_time', iskey=False, label = 'Response Time', datatype='metric', units='s', position=2).save()

wid = Widget(report=overall, title="Locations by Response Time", 
             row=3, col=2, rows=10, colwidth=6, 
             options = {'key': 'group_name',
                        'values': ['response_time']},
             module="yui3", uiwidget="BarWidget",
             uioptions = {'minHeight': 300})

wid.save()
wid.tables.add(dt)

#
# Google Map example
#

# Google Map example
themap = Report(title="Map")
themap.save()

# Define a table, group by location
dt = Table(name='maploc', module='profiler', device=tm08, duration=60, rows=20,
           filterexpr = 'host 10.99/16',
           options={'groupby': 'host_group'})
dt.save()
Column(table=dt, name='group_name', iskey=True, label = 'Group Name', position=1).save()
Column(table=dt, name='avg_bytes', iskey=False, label = 'Avg Bytes/s', datatype='bytes', units='B/s', position=2).save()

# Map wdiget on top of that table
wid = Widget(report=themap, title="Map",
             row=2, col=2, colwidth=12,
             options = {'key': 'group_name',
                        'value': 'avg_bytes'},
             module="google_maps", uiwidget="MapWidget",
             uioptions = {'minHeight': 500})
wid.save()
wid.tables.add(dt)

#
# Define a Table
#
#dt = Table(name='ifs_day', module='profiler', duration=(60*24), resolution=60,
#           options={'device': profiler.id,
#                    'groupby': 'interface'})
#dt.save()
#dt.add_columns(['interface_dns',
#                'avg_util',
#                'avg_bytes',
#                'avg_pkts',
#                'avg_conns_active',
#                'total_conns_rsts_pct',
#                'total_bytes_rtx_pct',
#                'response_time',
#                'network_rtt',
#                'server_delay'],
#               'avg_util')
#
#wid = Widget(report=overall, title="Interfaces (last day)", 
#             row=4, col=1, rows=1000, colwidth=12,
#             module="yui3", uiwidget="TableWidget", uioptions = {'minHeight': 300})
#wid.save()
#wid.tables.add(dt)

#
# Define a Shark Report and Table
#
shark_report = Report(title="Shark Report")
shark_report.save()

dt = Table(name='Packet Traffic', module='shark', device=v10, duration=10,
           options={'view': 'jobs/Flyscript-tests-job',
                    })
dt.save()
Column(table=dt, name='ip_src', iskey=True, label='Source IP', position=1,
       options=shark_ColumnOptions(extractor='ip.src').__dict__).save()
Column(table=dt, name='ip_dst', iskey=True, label='Dest IP', position=2,
       options=shark_ColumnOptions(extractor='ip.dst').__dict__).save()
Column(table=dt, name='generic_packets', iskey=False, label='Packets', position=3,
       options=shark_ColumnOptions(extractor='generic.packets', operation='sum').__dict__).save()

wid = Widget(report=shark_report, title="Shark Packets (last 10 minutes)",
             row=1, col=1, rows=1000, colwidth=12,
             module="yui3", uiwidget="TableWidget", uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

exit(0)

dt = Table(name='MicroburstsTotal', module='shark', duration=10,
           options={'device': shark.id,
                    'aggregated': True,
                    'view': 'jobs/Flyscript-tests-job',
                    })
dt.save()
dt.add_columns([
     'max_microburst_1ms_packets',
     'max_microburst_10ms_packets',
     'max_microburst_100ms_packets',
])
wid = Widget(report=shark_report, title="Microburst Packets (last 10 minutes)",
             row=2, col=1, rows=1000, colwidth=12,
             module="yui3", uiwidget="TableWidget", uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)

dt = Table(name='MicroburstsTime', module='shark', duration=10,
           options={'device': shark.id,
                    'aggregated': False,
                    'view': 'jobs/Flyscript-tests-job',
           })

dt.save()
dt.add_columns([
    'time',
    'max_microburst_1ms_packets',
#    'max_microburst_10ms_packets',
#    'max_microburst_100ms_packets',
    ])
wid = Widget(report=shark_report, title="Microburst Packets Timeseries (last 10 minutes)",
             row=3, col=1, rows=1000, colwidth=12,
             options={'axes': {'0': {'title': 'pkts/ms',
                                     'position': 'left',
                                     'columns': ['max_microburst_1ms_packets']}
             }},
             module="yui3", uiwidget="TimeSeriesWidget", uioptions = {'minHeight': 300})
wid.save()
wid.tables.add(dt)
#

exit(0)

translations = { "Avg Bytes/s": "平均バイト数/秒",
                 "Overall Traffic (last hour)": "全てのトラッフィック (過去１時間以内)",
                 "Traffic for hosts in  10.99/16" : "10.99/16サブネット内のホストへのトラッフィック",
                 "Traffic for hosts in  10.99.15/24" : "10.99.15/24サブネット内のホストへのトラッフィック",
                 "Total Bytes" : "合計バイト数",
                 "Locations by Bytes" : "場所別　合計バイト数/秒の割合",
                 "Location" : "場所",
                 "Top Locations by Response Time": "場所別の応答時間（秒）",
                 "Interface" : "インターフェイス",
                 "% Util" : "使用率（％）",
                 "Avg Pkts/s": "平均パケット数/秒",
                 "Active Conns/s": "アクティブな接続数/秒",
                 "% Resets" : "（TCP）リセット率（％）",
                 "% Retrans" : "再送信率（％）",
                 "Resp Time (ms)": "応答時間（ミリ秒）",
                 "Network RTT (ms)": "ネットワークの往復時間（ミリ秒）",
                 "Srv Delay (ms)": "サーバーの遅延時間（ミリ秒）",
                 "": "インターフェイス （過去１日間以内）" }



Column(source='profiler', name='time', source_name='time', label = 'Time', datatype='time').save()
Column(source='profiler', name='host_ip', source_name='host_ip', label = 'Host IP').save()
Column(source='profiler', name='avg_bytes', source_name='avg_bytes', label = 'Avg Bytes/s', units = 'B/s', datatype='bytes').save()
Column(source='profiler', name='group_name', source_name='group_name', label = 'Group Name').save()
Column(source='profiler', name='total_bytes', source_name='total_bytes', label = 'Total Bytes', datatype='bytes').save()
Column(source='profiler', name='avg_pkts', source_name='avg_pkts', label = 'Avg Pkts/s', datatype='metric').save()
Column(source='profiler', name='avg_conns_active', source_name='avg_conns_active', label = 'Active Conns/s', datatype='metric').save()
Column(source='profiler', name='total_conns_rsts_pct', source_name='total_conns_rsts_pct', label = '% Resets', datatype='metric').save()
Column(source='profiler', name='total_bytes_rtx_pct', source_name='total_bytes_rtx_pct', label = '% Retrans', datatype='metric').save()
Column(source='profiler', name='response_time', source_name='response_time', label = 'Resp Time (ms)', datatype='metric').save()
Column(source='profiler', name='network_rtt', source_name='network_rtt', label = 'Network RTT (ms)', datatype='metric').save()
Column(source='profiler', name='server_delay', source_name='server_delay', label = 'Srv Delay (ms)', datatype='metric').save()
Column(source='profiler', name='avg_util', source_name='avg_util', label = '% Util').save()
Column(source='profiler', name='interface_dns', source_name='interface_dns', label = 'Interface').save()

Column(source='shark', name='time', source_name='generic.absolute_time', source_key='True', label='Time (ns)').save()
Column(source='shark', name='ip_src', source_name='ip.src', source_key='True', label='Source IP').save()
Column(source='shark', name='ip_dst', source_name='ip.dst', source_key='True', label='Destination IP').save()
Column(source='shark', name='generic_packets', source_name='generic.packets', label='Packets').save()
Column(source='shark', name='http_duration_max', source_name='http.duration', source_operation='max', label='Max Duration').save()
Column(source='shark', name='http_duration_avg', source_name='http.duration', source_operation='avg', label='Avg Duration').save()
Column(source='shark', name='max_microburst_1ms_packets', source_name='generic.max_microburst_1ms.packets', source_operation='max', label='Microburst 1ms Pkts').save()
Column(source='shark', name='max_microburst_10ms_packets', source_name='generic.max_microburst_10ms.packets',source_operation='max',  label='Microburst 10ms Pkts').save()
Column(source='shark', name='max_microburst_100ms_packets', source_name='generic.max_microburst_100ms.packets',source_operation='max',  label='Microburst 100ms Pkts').save()
