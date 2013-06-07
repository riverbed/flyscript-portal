# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import time, datetime
import logging
import threading
import subprocess
import shlex
import binascii
import re
import string
import datetime
import pandas
import numpy
import os

from rvbd.common.exceptions import RvbdHTTPException
from rvbd.common.jsondict import JsonDict

from apps.datasource.models import Column, Device, Table
from apps.datasource.devicemanager import DeviceManager

logger = logging.getLogger(__name__)
lock = threading.Lock()

class TableOptions(JsonDict):
    _default = {'pcapfile': None}
    
class ColumnOptions(JsonDict):
    _default = {'field': None,
                'fieldtype': 'string', # float, int, time
                'operation': 'sum'}
    _required = ['field']

class TSharkTable:
    @classmethod
    def create(cls, name, **kwargs):
        return Table.create(name, module=__name__, **kwargs)

def tofloat(x):
    try:
        return float(x)
    except:
        return 0

def toint(x):
    try:
        return int(x)
    except:
        return 0

def totimeint(s):
    (a,b) = s.split(".")
    return int(a) * 1000000000 + int(b)

class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        table = self.table
        columns = table.get_columns(synthetic=False)
        options = table.options

        trafficexpr = self.job.combine_filterexprs()
        pcapfile = options.pcapfile
        if pcapfile is None:
            if trafficexpr:
                m = re.match("pcap ([^ ]+) *(.*)$", trafficexpr)
                if m:
                    pcapfile = m.group(1)
                    trafficexpr = m.group(2)

        if not pcapfile:
            raise ValueError("No pcap file specified")
        elif not os.path.exists(pcapfile):
            raise ValueError("No such file: %s" % pcapfile)
        
        command = "tshark -r %s -T fields -E occurrence=f -E separator=," % pcapfile

        keys = []
        basecolnames = [] # list of colummns
        fields = {} # dict by field name of the base (or first) column to use this field
        ops = {}
        groupbytime = None
        for tc in columns:
            tc_options = tc.options
            if tc_options.field in fields.keys():
                # Asking for the same field name twice doesn't work, but
                # is useful when aggregating and choosing a different operation
                # like "min", or "max".  Will populate these columns later
                continue
            command = command + (" -e %s" % tc_options.field)
            fields[tc_options.field] = tc.name
            basecolnames.append(tc.name)
            if tc.iskey:
                keys.append(tc.name)
                if tc.datatype == 'time':
                    groupbytime = tc.name
            else:
                ops[tc.name] = tc_options.operation

        if trafficexpr:
            command = command + (" -R '%s'" % trafficexpr)

        print "command: %s" % command
        proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)

        data = []
        while proc.poll() is None:
            line = proc.stdout.readline().rstrip()
            if not line:
                continue
            cols = line.split(',')
            if len(cols) != len(basecolnames):
                logger.error("Could not parse line: %s" % line)
                continue
            data.append(cols)

    
        df = pandas.DataFrame(data, columns=basecolnames)
        # At this point we have a dataframe with the one column for each
        # unique field (the first column to reference the field)
        
        if table.rows > 0:
            df = df[:table.rows]

        logger.info("Data returned:\n%s", df[:3])

        # Convert the data into the right format
        for tc in columns:
            if tc.name not in basecolnames:
                continue 
            tc_options = tc.options
            if tc_options.fieldtype == "float":
                df[tc.name] = df[tc.name].map(tofloat)
            elif tc_options.fieldtype == "int":
                df[tc.name] = df[tc.name].map(toint)
            elif tc.datatype == "time":
                df[tc.name] = pandas.DatetimeIndex(df[tc.name].map(totimeint))

        colnames = [col.name for col in columns]
        self.data = df.ix[:,colnames].values.tolist()
        return True
