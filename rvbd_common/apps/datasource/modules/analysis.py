# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import logging

from rvbd.common.jsondict import JsonDict
from rvbd_common.apps.datasource.models import Column, Job, Table, BatchJobRunner

logger = logging.getLogger(__name__)

class TableOptions(JsonDict):
    _default = { 'tables': None,
                 'func' : None,
                 'params': None }

    _required = [ 'tables', 'func' ]
    
class AnalysisException(Exception):
    def _init__(self, message, *args, **kwargs):
        self.message = message
        super(AnalysisException, self).__init__(*args, **kwargs)

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

    `params` is an optional dictionary of parameters to pass to `func`
    
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
    def create(cls, name, tables, func,
               columns=[], params=None,
               copy_fields=True,
               **kwargs):
        """ Class method to create an AnalysisTable.
        """
        options = TableOptions(tables=tables, func=func,
                               params=params)
        table = Table (name=name, module=__name__, 
                       options=options, **kwargs)
        table.save()
        
        if columns:
            for c in columns:
                Column.create(table, c)

        keywords = []
        if tables and copy_fields:
            for table_id in tables.values():
                for f in Table.objects.get(id=table_id).fields.all():
                    if f.keyword not in keywords:
                        table.fields.add(f)
                        keywords.append(f.keyword)
        return table

class TableQuery:
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def __unicode__(self):
        return "<AnalysisTable %s>" % (self.job)

    def __str__(self):
        return "<AnalysisTable %s>" % (self.job)

    def mark_progress(self, progress):
        # Called by the analysis function
        self.job.mark_progress(70 + (progress * 30)/100)
        
    def run(self):
        # Collect all dependent tables
        options = self.table.options
        logger.debug("%s: dependent tables: %s"  % (self, options.tables))
        deptables = options.tables
        depjobids = {}
        batch = BatchJobRunner(self.job, max_progress=70)
        for (name, id) in deptables.items():
            id = int(id)
            deptable = Table.objects.get(id=id)
            job = Job.create(table=deptable, criteria=self.job.criteria.build_for_table(deptable))
            batch.add_job(job)
            logger.debug("%s: starting dependent job %s" % (self, job))
            depjobids[name] = (job.id)
                    
        batch.run()

        logger.debug("%s: All dependent jobs complete, collecting data" % str(self))
        # Create dataframes for all tables
        dfs = {}
        
        failed = False
        for (name, id) in depjobids.items():
            job = Job.objects.get(id=id)
                
            if job.status == job.ERROR:
                self.job.mark_error("Dependent Job failed: %s" % (job.message))
                failed = True
                break
            
            f = job.data()
            dfs[name] = f
            logger.debug("%s: Table[%s] - %d rows" % (self, name, len(f) if f is not None else 0))

        if failed:
            return False

        logger.debug ("%s: Calling analysis function %s" % (self, str(options.func)))

        try:
            df = options.func(self, dfs, self.job.criteria, params=options.params)
        except AnalysisException as e:
            self.job.mark_error("Analysis function %s failed: %s" % (options.func, e.message))
            logger.exception("%s raised an exception" % (self))
            return False
        except Exception as e:
            self.job.mark_error("Analysis function %s failed: %s" % (options.func, str(e)))
            logger.exception("%s: Analysis function %s raised an exception" %
                             (self, options.func))
            return False
            
        # Sort according to the defined sort columns
        if df is not None:
            if self.table.sortcol:
                n = self.table.sortcol.name
                sorted = df.sort(n, ascending=False)
                # Move NaN rows to the end
                df = (sorted[sorted[n].notnull()]
                      .append(sorted[sorted[n].isnull()]))

            if self.table.rows > 0:
                self.data = df[:self.table.rows]
            else:
                self.data = df
        else:
            self.data = None
        
        logger.debug("%s: completed successfully"  % (self))
        return True
