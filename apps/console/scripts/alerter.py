#!/usr/bin/env python

# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

"""
Simple example demonstrating ability for multi-stage user defined policy.

Requires installation of `pysnmp` python library to support sending snmp traps

example call signature:
python alerter.py tm08-1.lab.nbttech.com -u admin -p admin --expr1 'app WEB' --trigger1 '> 100' \
    --column1 'avg_bytes' --expr2 'app VoIP' --trigger2 '> 6100' --column2 'avg_bytes'

"""

import sys
import datetime

from rvbd.profiler.app import ProfilerApp
from rvbd.profiler.filters import TrafficFilter
from rvbd.profiler.report import TrafficSummaryReport
from rvbd.common.utils import Formatter
from rvbd.common import timeutils

from pysnmp.entity.rfc3413.oneliner import ntforg
from pysnmp.proto import rfc1902

import re
import time
import optparse


def safe_lambda(trigger):
    """ Return a reasonably safe lambda function for the given trigger
    """
    regex = re.compile('^[ <>=]+[0-9.]+[ ]*$')
    trigger = trigger.strip().strip('"').strip("'")
    if re.match(regex, trigger):
        return lambda x: eval('%s %s' % (x, trigger))
    return None


class AlerterApp(ProfilerApp):

    def add_options(self, parser):
        group = optparse.OptionGroup(parser, "Trigger Options")
        group.add_option('--expr1', help="Initial traffic expression to trigger on")
        group.add_option('--trigger1', help="First Trigger (e.g. '> 1000')")
        group.add_option('--column1', help="Column to apply trigger against (e.g. 'avg_bytes')")
        group.add_option('--expr2', help="(Optional) Secondary traffic expression to trigger on")
        group.add_option('--trigger2', help="(Optional) Second Trigger (e.g. '< 10')")
        group.add_option('--column2', help="(Optional) Column to apply trigger against (e.g. 'network_rtt')")
        group.add_option('--refresh', help="Refresh interval for queries in Seconds (default: 5)", default=5)
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "TRAP Options")
        group.add_option('--eoid', help="Enterprise OID (defaults to Cascade Profiler ID: '1.3.6.1.4.1.7054.70.0.' )", 
                         default='1.3.6.1.4.1.7054.70.0.')
        group.add_option('--trapid', help="Trap code indicator (default: 99)", default='99')
        group.add_option('--community', help="Community name (default: 'public')", default='public')
        group.add_option('--manager_ip', help="Destination server for Traps (default: '127.0.0.1')", 
                         default='127.0.0.1')
        group.add_option('--trap-description', help="Description to use within Trap (default: 'FlyScript SDK Trap Alert')", 
                         default='FlyScript SDK Trap Alert')
        group.add_option('--severity', help="Severity of Trap (default: '70')", default=70)
        group.add_option('--trap-url', help="URL to include in Trap Message (default: 'http://localhost')", 
                         default='http://localhost')
        group.add_option('--alert-level', help="Alert level of Trap (1=Low, 2=Medium, 3=High) (default: 2)", default=2)
        parser.add_option_group(group)

    def validate_args(self):
        super(AlerterApp, self).validate_args()

        if not self.options.trigger1:
            self.optparse.error('At least trigger1 must be specified.')

    def send_trap(self):
        """ Send a SNMP trap with id `trapid` to the IP address `manager`
        """
        oid = self.options.eoid             # cascade enterprise Object ID
        trapid = self.options.trapid        # base string for trap indicators

        community = self.options.community
        manager_ip = self.options.manager_ip

        severity = self.options.severity
        description = self.trap_description
        url = self.options.trap_url
        alert_level = self.options.alert_level
        now = timeutils.datetime_to_seconds(datetime.datetime.now())

        trapname = '.'.join([oid, trapid])

        ntf = ntforg.NotificationOriginator()

        err = ntf.sendNotification(ntforg.CommunityData(community),
                                   ntforg.UdpTransportTarget((manager_ip, 162)),
                                   'trap',
                                   trapname, 
                                   ('1.3.6.1.2.1.1.3.0', rfc1902.Integer(0)),                         # Uptime
                                   ('1.3.6.1.4.1.7054.71.2.1.0', rfc1902.Integer(severity)),            # Severity
                                   ('1.3.6.1.4.1.7054.71.2.3.0', rfc1902.OctetString(description)),
                                   ('1.3.6.1.4.1.7054.71.2.4.0', rfc1902.Integer(0)),                   # Event ID
                                   ('1.3.6.1.4.1.7054.71.2.5.0', rfc1902.OctetString(url)),
                                   ('1.3.6.1.4.1.7054.71.2.7.0', rfc1902.Integer(alert_level)),         # Alert Level
                                   ('1.3.6.1.4.1.7054.71.2.8.0', rfc1902.Integer(now)),                 # Start Time
                                   ('1.3.6.1.4.1.7054.71.2.16.0', rfc1902.Integer(0)),                  # Source Count
                                   ('1.3.6.1.4.1.7054.71.2.18.0', rfc1902.Integer(0)),                  # Destination Count
                                   ('1.3.6.1.4.1.7054.71.2.20.0', rfc1902.Integer(0)),                  # Protocol Count
                                   ('1.3.6.1.4.1.7054.71.2.22.0', rfc1902.Integer(0)),                  # Port Count                                
                                   )

    def run_query(self, report, column, trafficexpr, trigger):
        report.run(columns=column, groupby='hos', trafficexpr=trafficexpr)
        data = report.get_data()
        if data:
            for row in data:
                for item in row:
                    if item and trigger(item):
                        return item
        return None

    def update_description(self, result, result2):
        """ Creates string to highlight what threshold/trigger was crossed
        """
        desc = ''
        if result:
            desc = 'Trigger1: %s %s' % (result, self.options.trigger1)
            if result2:
                desc = '%s --> Trigger2: %s %s' % (desc, result2, self.options.trigger2)
        if desc:
            self.trap_description = '%s: %s' % (self.options.trap_description, desc)
        else:
            self.trap_description = self.options.trap_description

    def main(self):
        self.tfilter1 = TrafficFilter(self.options.expr1)
        self.report1 = TrafficSummaryReport(self.profiler)
        self.columns_report1 = self.profiler.get_columns([self.options.column1])
        self.trigger1 = safe_lambda(self.options.trigger1)

        if self.options.trigger2 and self.options.column2 and self.options.expr2:
            self.tfilter2 = TrafficFilter(self.options.expr2)
            self.report2 = TrafficSummaryReport(self.profiler)
            self.columns_report2 = self.profiler.get_columns([self.options.column2])
            self.trigger2 = safe_lambda(self.options.trigger2)
        else:
            self.trigger2 = None

        try:
            while 1:
                print 'Running report 1 ...'
                alert_flag = False
                result = None
                result2 = None

                result = self.run_query(self.report1,
                                        self.columns_report1, 
                                        self.tfilter1, 
                                        self.trigger1)
                if result:
                    if self.trigger2:
                        print 'Trigger 1 passed, running report 2 ...'
                        result2 = self.run_query(self.report2,
                                                 self.columns_report2, 
                                                 self.tfilter2, 
                                                 self.trigger2)
                        if result2:
                            print 'Trigger 2 passed ...'
                            alert_flag = True
                    else:
                        print 'Trigger 1 passed ...'
                        alert_flag = True
                if alert_flag:
                    print 'ALERT ALERT!'
                    self.update_description(result, result2)
                    self.send_trap()

                time.sleep(self.options.refresh)

        except KeyboardInterrupt:
            print 'Exiting ...'
            sys.exit(0)


if __name__ == '__main__':
    AlerterApp().run()
