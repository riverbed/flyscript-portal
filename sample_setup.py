# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from random import randint
import sys, os
import pickle
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import *
from apps.report.models import *

profiler = Device(name="tm08-1",
                  sourcetype="profiler",
                  host="tm08-1.lab.nbttech.com",
                  port=443,
                  username="admin",
                  password="admin")
profiler.save()

Column(source='profiler', name='time', source_name='time', label = 'Time', datatype='time').save()
Column(source='profiler', name='avg_bytes', source_name='avg_bytes', label = 'Avg Bytes/s', datatype='bytes').save()
Column(source='profiler', name='group_name', source_name='group_name', label = 'Group Name').save()
Column(source='profiler', name='total_bytes', source_name='total_bytes', label = 'Total Bytes', datatype='bytes').save()
Column(source='profiler', name='avg_pkts', source_name='avg_pkts', label = 'Avg Pkts/s', datatype='metric').save()
Column(source='profiler', name='avg_conns_active', source_name='avg_conns_active', label = 'Active Conns/s', datatype='metric').save()
Column(source='profiler', name='total_conns_rsts_pct', source_name='total_conns_rsts_pct', label = '% Resets', datatype='metric').save()
Column(source='profiler', name='total_bytes_rtx_pct', source_name='total_bytes_rtx_pct', label = '% Retrans', datatype='metric').save()
Column(source='profiler', name='response_time', source_name='response_time', label = 'Resp Time (ms)', datatype='metric').save()
Column(source='profiler', name='network_rtt', source_name='network_rtt', label = 'Network RTT (ms)', datatype='metric').save()
Column(source='profiler', name='server_delay', source_name='server_delay', label = 'Srv Delay (ms)', datatype='metric').save()
Column(source='profiler', name='avg_util', source_name='avg_util', label = '% Util')
Column(source='profiler', name='interface_dns', source_name='interface_dns', label = 'Interface').save()

# Define a TimeSeries 
dt = Table(source='profiler', duration=60, options={'device': profiler.id,
                                                        'realm': 'traffic_overall_time_series',
                                                        'groupby': 'time'})
dt.save()
dt.add_columns(['time', 'avg_bytes'])
               
main = Report(title="Main")
main.save()

interfaces = Report(title="Interfaces")
interfaces.save()

wid = Widget(report=main, title="Overall Traffic (last hour)", table = dt,
             row=1, col=1, colwidth=12,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']}
                               }},
             uilib="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})

wid.save()

# Define a TimeSeries 
dt = Table(source='profiler', duration=60,
               filterexpr = 'host 10.99/16',
               options={'device': profiler.id,
                        'realm': 'traffic_overall_time_series',
                        'groupby': 'time'})
dt.save()
dt.add_columns(['time', 'avg_bytes'])

wid = Widget(report=main, title="Traffic for hosts in  10.99/16 (last hour)", table = dt,
             row=2, col=1, colwidth=6,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']}
                               }},
             uilib="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})

wid.save()

# Define a TimeSeries 
dt = Table(source='profiler', duration=60,
               filterexpr = 'host 10.99.15/24',
               options={'device': profiler.id,
                        'realm': 'traffic_overall_time_series',
                        'groupby': 'time'})
dt.save()
dt.add_columns(['time', 'avg_bytes'])

wid = Widget(report=main, title="Traffic for hosts in  10.99.15/24 (last hour)", table = dt,
             row=2, col=2, colwidth=6,
             options={'axes': {'0': {'title': 'bytes/s',
                                     'position': 'left',
                                     'columns': ['avg_bytes']}
                               }},
             uilib="yui3", uiwidget="TimeSeriesWidget",
             uioptions = {'minHeight': 300})

wid.save()

#######

# Define a Table
dt = Table(source='profiler', duration=60,
               options={'device': profiler.id,
                        'groupby': 'host_group'})
dt.save()
dt.add_columns(['group_name', 'total_bytes'], 'total_bytes')

wid = Widget(report=main, title="Locations by Bytes", table = dt, 
             row=3, col=1, rows=10, colwidth=6, 
             options = {'key': 'group_name',
                        'value': 'total_bytes'},
             uilib="yui3", uiwidget="PieWidget",
             uioptions = {'minHeight': 300})

wid.save()

# Define a Table
dt = Table(source='profiler', duration=60,
               options={'device': profiler.id,
                        'groupby': 'host_group'})
dt.save()
dt.add_columns(['group_name', 'response_time'], 'response_time')

wid = Widget(report=main, title="Locations by Response Time", table = dt, 
             row=3, col=2, rows=10, colwidth=6, 
             options = {'key': 'group_name',
                        'values': ['response_time']},
             uilib="yui3", uiwidget="BarWidget",
             uioptions = {'minHeight': 300})

wid.save()

#
# Define a Table
#
dt = Table(source='profiler', duration=(60*24), resolution=60,
           options={'device': profiler.id,
                    'groupby': 'interface'})
dt.save()
dt.add_columns(['interface_dns', 'avg_utl',
                'avg_bytes',
                'avg_pkts',
                'avg_conns_active',
                'total_conns_rsts_pct',
                'total_bytes_rtx_pct',
                'response_time',
                'network_rtt',
                'server_delay'],
               'avg_util')

wid = Widget(report=main, title="Interfaces (last day)", table = dt, 
             row=4, col=1, rows=1000, colwidth=12,
             uilib="yui3", uiwidget="TableWidget", uioptions = {'minHeight': 300})
wid.save()

translations = { "Avg Bytes/s": "平均バイト数/秒",
                 "Overall Traffic (last hour)": "全てのトラッフィック (過去１時間以内)",
                 "Traffic for hosts in  10.99/16 (last hour)" : "10.99/16サブネット内のホストへのトラッフィック (過去１時間以内)",
                 "Traffic for hosts in  10.99.15/24 (last hour)" : "10.99.15/24サブネット内のホストへのトラッフィック (過去１時間以内)",
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
