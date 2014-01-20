# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import logging
import threading
import subprocess
import shlex
import os

import pandas
from rvbd.common.jsondict import JsonDict

from django.forms.widgets import FileInput

from rvbd_common.apps.datasource.models import Table, TableField
from rvbd_common.apps.datasource.forms import FileSelectField, fields_add_resolution


logger = logging.getLogger(__name__)
lock = threading.Lock()

class ColumnOptions(JsonDict):
    _default = {'field': None,
                'fieldtype': 'string',  # float, int, time
                'operation': 'sum'}
    _required = ['field']


def fields_add_pcapfile(obj,
                        keyword = 'pcapfile',
                        initial=None
                        ):
    field = TableField(keyword='pcapfile',
                       label='PCAP File',
                       field_cls=FileSelectField,
                       field_kwargs={'widget': FileInput})
    field.save()
    obj.fields.add(field)
    
class TSharkTable:
    @classmethod
    def create(cls, name, resolution=1, **kwargs):

        if resolution and isinstance(resolution, int):
            resolution = "%dsec" % resolution

        criteria = {'resolution': resolution}

        table = Table.create(name, module=__name__, criteria=criteria, **kwargs)
        fields_add_resolution(table)
        fields_add_pcapfile(table)
        return table
    

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
    (a, b) = s.split(".")
    return int(a) * 1000000000 + int(b)

class TableQuery:
    # Used by Table to actually run a query
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        table = self.table
        columns = table.get_columns(synthetic=False)

        trafficexpr = self.job.combine_filterexprs()

        # process Report/Table Criteria
        #from IPython import embed; embed()
        table.apply_table_criteria(self.job.criteria)

        pcapfile = self.job.criteria.pcapfile

        if not pcapfile:
            raise ValueError("No pcap file specified")
        elif not os.path.exists(pcapfile):
            raise ValueError("No such file: %s" % pcapfile)
        
        command = "tshark -r %s -T fields -E occurrence=f -E separator=," % pcapfile

        keys = []
        basecolnames = []  # list of colummns
        fields = {}  # dict by field name of the base (or first) column to use this field
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

        msg = "tshark command: %s" % command
        #print msg
        logger.debug(msg)
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
