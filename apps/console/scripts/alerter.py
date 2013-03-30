#!/usr/bin/env python

# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.



"""
Simple example demonstrating ability for multi-stage user defined policy.

Requires installation of `pysnmp` python library to support sending snmp traps

example call signature:
python alerter.py tm08-1.lab.nbttech.com -u admin -p admin --expr1 'app WEB' --trigger1 '> 100' \
    --column1 'avg_bytes' --expr2 'app VoIP' --trigger2 '> 6100' --column2 'avg_bytes'

"""


from rvbd.profiler.app import ProfilerApp
from rvbd.profiler.filters import TrafficFilter
from rvbd.profiler.report import TrafficSummaryReport, TrafficOverallTimeSeriesReport
from rvbd.common.utils import Formatter

import pysnmp
from pysnmp.entity.rfc3413.oneliner import ntforg
from pysnmp.proto import rfc1902

import re
import time
import optparse

def safe_lambda(trigger):
    """ Return a reasonably safe lambda function for the given trigger
    """
    regex = re.compile('^[ <>=]+[0-9.]+[ ]*$')
    trigger = trigger.strip()
    if re.match(regex, trigger):
        return lambda x:eval('%s %s' % (x, trigger))
    return None

def snmptrap(manager_ip, trapid):
    """ Send a SNMP trap with id `trapid` to the IP address `manager`
    """
    oid = '1.3.6.1.4.1.7054.70'             # cascade enterprise Object ID
    trapbase = '1.3.6.1.4.1.7054.70.0.'     # base string for trap indicators

    trapname = trapbase + trapid

    ntf = ntforg.NotificationOriginator()

    err = ntf.sendNotification(ntforg.CommunityData('public'),
                               ntforg.UdpTransportTarget((manager_ip, 162)),
                               'trap',
                               trapname)


class AlerterApp(ProfilerApp):

    def add_options(self, parser):
        group = optparse.OptionGroup(parser, "Alerter Options")
        group.add_option('--expr1', help="Initial traffic expression to trigger on")
        group.add_option('--trigger1', help="First Trigger (e.g. '> 1000')")
        group.add_option('--column1', help="Column to apply trigger against (e.g. 'avg_bytes')")
        group.add_option('--expr2', help="Secondary traffic expression to trigger on")
        group.add_option('--trigger2', help="Second Trigger (e.g. '< 10')")
        group.add_option('--column2', help="Column to apply trigger against (e.g. 'network_rtt')")

        parser.add_option_group(group)

    def validate_args(self):
        super(AlerterApp, self).validate_args()

        if not self.options.trigger1 or not self.options.trigger2:
            self.optparse.error('Both triggers must be specified.')

    def main(self):
        self.tfilter1 = TrafficFilter(self.options.expr1)
        self.tfilter2 = TrafficFilter(self.options.expr2)

        self.report1 = TrafficSummaryReport(self.profiler)
        self.columns_report1 = self.profiler.get_columns([self.options.column1])
        self.trigger1 = safe_lambda(self.options.trigger1)

        self.report2 = TrafficSummaryReport(self.profiler)
        self.columns_report2 = self.profiler.get_columns([self.options.column2])
        self.trigger2 = safe_lambda(self.options.trigger2)

        while 1:
            print 'Running report 1 ...'
            self.report1.run(columns=self.columns_report1,
                             groupby='hos',
                             trafficexpr=self.tfilter1)
            data = self.report1.get_data()

            if data and any(self.trigger1(y) for x in data for y in x):
                print 'Trigger 1 passed, running report 2 ...'
                self.report2.run(columns=self.columns_report2,
                                 groupby='hos',
                                 trafficexpr=self.tfilter2)
                data2 = self.report2.get_data()
                if data2 and any(self.trigger2(y) for x in data for y in x):
                    print 'ALERT ALERT!'
                    snmptrap('127.0.0.1', '99')

            time.sleep(5)

AlerterApp().run()




