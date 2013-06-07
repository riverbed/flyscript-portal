# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import json
import time
import pickle
import logging
import threading
import pandas
from random import randint

from rvbd.common.jsondict import JsonDict
from apps.datasource.models import Column, Job, Table

logger = logging.getLogger(__name__)

class TableOptions(JsonDict):
    _default = { 'tables': None,
                 'func' : None }
    _required = [ 'tables', 'func' ]
    
class AnalysisTable:
    """
    An AnalysisTable builds on other tables, running them first to collect
    data, then extracting the data as pandas.DataFrame objects.  The
    set of DataFrames is then passed to a user defined function that
    must return a DataFrame with columns matching the Columns associated
    with this Table.

    `tables` is hashmap of dependent tables, mapping a names expected
        by the analysis functon to table ids

    `func` is a pointer to the user defined analysis function
    
    For example, consider an input of two tables A and B, and an
    AnalysisTable that simply concatetanates A and B:

        A = Table.create('A')
        Column.create(A, 'host')
        Column.create(A, 'bytes')

        B = Table.create('B')
        Column.create(B, 'host')
        Column.create(B, 'pkts')

        from config.reports.helpers.analysis_funcs import combine_by_host
        Combined = AnalysisTable.create('Combined',
                                        tables = { 't1' : A.id,
                                                   't2' : B.id },
                                        func = combine_by_host)
        Column.create(Combined, 'host')
        Column.create(Combined, 'bytes')
        Column.create(Combined, 'pkts')
       
    Then in config/reports/helpers/analysis_func.py

        def combine_by_host(dst, srcs):
            # Get the pandas.DataFrame objects for t1 and t2
            t1 = srcs['t1']
            t2 = srcs['t2']

            # Now create a new DataFrame that joins these
            # two tables by the 'host'
            df = pandas.merge(t1, t2, left_on='host', right_on='host', how='outer')
            return df

    Note that the function must defined in a separate file in the 'helpers' directory.
    """

    @classmethod
    def create(cls, name, tables, func, duration=-1, columns=[]):
        """
        Class method to create an AnalysisTable.
        """
        t = Table(name=name, module=__name__, device=None, duration=duration,
                  options=TableOptions(tables=tables, func=func))
        t.save()

        if columns:
            for c in columns:
                Column.create(t, c)
                
        return t
    
class TableQuery:
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def run(self):
        # Collect all dependent tables
        options = self.table.options
        logger.debug("Analysis dependent tables: %s"  % options.tables)
        deptables = options.tables
        depjobids = {}
        for (name, id) in deptables.items():
            id = int(id)
            logger.debug("Analysis dependent table %d" % id)
            deptable = Table.objects.get(id=id)
            job = Job(table=deptable, criteria=self.job.criteria.build_for_table(deptable))
            job.save()
            job.start()
            depjobids[name] = (job.id)
                    
        # Poll until all jobs are complete
        done=False
        while not done:
            done=True
            for jid in depjobids.values():
                job = Job.objects.get(id=jid)
                d = job.done()
                logger.debug("Job %s - %s" % (str(job), d))
                if not d:
                    done=False
                    break
            time.sleep(0.5)

        logger.debug("Analysis job %s - all dependent jobs complete, collecting data" % str(self.job))
        # Create dataframes for all tables
        dfs = {}

        for (name, id) in depjobids.items():
            job = Job.objects.get(id=id)
            if job.status == job.ERROR:
                self.job.status = job.ERROR
                raise ValueError("Dependent Job returned an error: %s" % (str(job)))

            f = job.pandas_dataframe()
            if f is None:
                logger.info("Dependent job returned no data: %s" % (str(job)))
                raise ValueError("Dependent Job returned no data: %s" % (str(job)))
            dfs[name] = f
            logger.debug("Table[%s]" % name)

        df = options.func(self.table, dfs)
        self.data = df.ix[:,[col.name for col in self.table.get_columns()]].values
        return True
    
