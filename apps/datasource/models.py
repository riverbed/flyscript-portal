# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
import sys
import json
import pickle
import logging
import traceback
import threading
import time
import hashlib
import importlib
import tokenize
import pandas

from StringIO import StringIO

from django.db import models
from django.db.models import Max

from rvbd.common.utils import DictObject
from rvbd.common.jsondict import JsonDict

from libs.fields import PickledObjectField

from project import settings

logger = logging.getLogger(__name__)

lock = threading.Lock()

#
# Device
#
class Device(models.Model):
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)
    host = models.CharField(max_length=200)
    port = models.IntegerField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    def __unicode__(self):
        return '%s (%s:%s)' % (self.name, self.host, self.port)

#
# Table
#
class Table(models.Model):
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)    # source module name
    device = models.ForeignKey(Device, null=True)
    filterexpr = models.TextField(null=True)
    duration = models.IntegerField(null=True)    # length of query in minutes
    resolution = models.IntegerField(default=60) # resolution of graph in seconds
    sortcol = models.ForeignKey('Column', null=True, related_name='Column')
    rows = models.IntegerField(default=-1)
    datafilter = models.TextField(null=True, blank=True)  # deprecated interface
                                                          # key/value separated by comma

    resample = models.BooleanField(default=False)
    options = PickledObjectField()
    
    @classmethod
    def create(self, name, module, **kwargs):
        t = Table(name=name, module=module, **kwargs)
        t.save()
        return t
    
    def __unicode__(self):
        return "%s (id=%s)" % (self.name, str(self.id))

    def get_columns(self, synthetic=True):
        if synthetic:
            return Column.objects.filter(table=self).order_by('position')
        else:
            return Column.objects.filter(table=self, synthetic=False).order_by('position')

    def compute_synthetic(self, indata):
        """
        Compute the synthetic columns from INDATA, a two-dimensional array
        of the non-synthetic columns.

        Synthesis occurs as follows:

        1. Compute all synthetic columns where compute_post_resample is False

        2. If the table is a time-based table with a defined resolution, the
           result is resampled.

        3. Any remaining columns are computed.
        """
        if len(indata) == 0:
            return []
        
        df = pandas.DataFrame(
            indata,
            columns = [col.name for col in self.get_columns(synthetic=False)]
            )
        
        all_columns = self.get_columns(synthetic=True)
        all_col_names = [c.name for c in all_columns]

        def compute(df, syncols):
            #logger.debug("Compute: syncol = %s" % ([c.name for c in syncols]))
            for syncol in syncols:
                expr = syncol.compute_expression
                g = tokenize.generate_tokens(StringIO(expr).readline)
                newexpr = ""
                getvalue = False
                getclose = False
                for ttype, tvalue, _, _, _ in g:
                    if getvalue:
                        if ttype != tokenize.NAME:
                            raise ValueError("Invalid token, expected {name}: %s" % tvalue)
                        elif tvalue not in all_col_names:
                            raise ValueError("Invalid column name: %s" % tvalue)
                        newexpr += "df['%s']" % tvalue
                        getclose = True
                        getvalue = False
                    elif getclose:
                        if ttype != tokenize.OP and tvalue != "}":
                            raise ValueError("Invalid syntax, expected {name}: %s" % tvalue)
                        getclose = False
                    elif ttype == tokenize.OP and tvalue == "{":
                        getvalue = True
                    else:
                        newexpr += tvalue

                df[syncol.name] = eval(newexpr)

        # 1. Compute synthetic columns where post_resample is False
        compute(df, [col for col in all_columns if (col.synthetic and
                                                    col.compute_post_resample is False)])

        # 2. Resample
        colmap = {}
        timecol = None
        for col in all_columns:
            colmap[col.name] = col
            if col.datatype == "time":
                timecol = col.name
        if timecol and self.resample:
            how = {}
            for k in df.keys():
                if k == timecol:
                    continue
                how[k] = colmap[k].resample.operation

            indexed = df.set_index(timecol)
            resampled = indexed.resample('%ss' % self.resolution, how).reset_index()
            df = resampled

        # 3. Compute remaining synthetic columns (post_resample is True)
        compute(df, [col for col in all_columns if (col.synthetic and
                                                    col.compute_post_resample is True)])


        # Replace NaN with None
        return df.where(pandas.notnull(df), None).ix[:,all_col_names].values.tolist()

class Column(models.Model):

    table = models.ForeignKey(Table)
    name = models.CharField(max_length=30)
    label = models.CharField(max_length=30, null=True)
    position = models.IntegerField()
    options = PickledObjectField()

    iskey = models.BooleanField(default=False)
    isnumeric = models.BooleanField(default=True)

    synthetic = models.BooleanField(default=False)
    compute_post_resample = models.BooleanField(default=False)
    compute_expression = models.CharField(max_length=300)
    resample_operation = models.CharField(max_length=300, default='sum')
    
    # datatype should be an enumeration: metric, bytes, time  XXXCJ make enumeration
    datatype = models.CharField(max_length=50, default='')

    units = models.CharField(max_length=50, default='') 

    def __unicode__(self):
        return self.label

    def save(self):
        if self.label is None:
            self.label = self.name
        super(Column, self).save()

    @classmethod
    def create(cls, table, name, label=None, datatype='', units='',
               iskey=False, issortcol=False, options=None, **kwargs):
        c = Column(table=table, name=name, label=label, datatype=datatype, units=units,
                   iskey=iskey, options=options, **kwargs)
        posmax = Column.objects.filter(table=table).aggregate(Max('position'))
        c.position = posmax['position__max'] or 1
        c.save()
        if issortcol:
            table.sortcol = c
            table.save()
        return c

class Criteria(DictObject):
    def __init__(self, starttime=None, endtime=None, duration=None, filterexpr=None, table=None, ignore_cache=False, *args, **kwargs):
        super(Criteria, self).__init__(*args, **kwargs)
        self.starttime = starttime
        self.endtime = endtime
        self.duration = duration
        self.filterexpr = filterexpr
        self.ignore_cache = ignore_cache

        self.orig_starttime = starttime
        self.orig_endtime = endtime
        self.orig_duration = duration
        
        if table:
            self.compute_times(table)
            

    def build_for_table(self, table):
        return Criteria(starttime=self.orig_starttime,
                        endtime=self.orig_endtime,
                        duration=self.orig_duration,
                        filterexpr=self.filterexpr,
                        ignore_cache=self.ignore_cache,
                        table=table)
                        
    def compute_times(self, table):
        if table.duration is None:
            return
        
        if self.endtime is None:
            self.endtime = time.time()

        # Snap backwards based on table resolution
        self.endtime = self.endtime - self.endtime % table.resolution

        if self.starttime is None:
            if self.duration is None:
                self.duration = table.duration*60

            self.starttime = self.endtime - self.duration

        self.starttime = self.starttime - self.starttime % table.resolution
            

#
# Job
#
class Job(models.Model):

    table = models.ForeignKey(Table)
    criteria = PickledObjectField(null=True)
    handle = models.CharField(max_length=100, default="")

    NEW = 0
    RUNNING = 1
    RUNNING_DEP = 2
    COMPLETE = 3
    ERROR = 4
    
    status = models.IntegerField(
        default=NEW,
        choices = ((NEW, "New"),
                   (RUNNING, "Running"),
                   (RUNNING_DEP, "Running dependent on another job"),
                   (COMPLETE, "Complete"),
                   (ERROR, "Error")))

    message = models.CharField(max_length=200, default="")
    progress = models.IntegerField(default=-1)
    remaining = models.IntegerField(default=-1)

    def __unicode__(self):
        return "<%s, table %s, pct %s%%>" % (self.table.name, self.status, self.progress)

    def compute_handle(self):
        h = hashlib.md5()
        h.update(str(self.table.id))
        h.update('.'.join([c.name for c in self.table.get_columns()]))
        h.update(json.dumps(self.criteria))
        return h.hexdigest()
    
    def get_depjob(self):
        jobs = Job.objects.filter(
            handle=self.handle,
            status__in=[self.RUNNING, self.COMPLETE, self.ERROR])

        if len(jobs) == 0:
            return None
        return jobs[0]

    def done(self):
        if self.status == Job.RUNNING_DEP:
            depjob = self.get_depjob()
            if not depjob:
                raise ValueError("Failed to find dependent job")
            self.progress = depjob.progress
            self.message = depjob.message
            self.remaining = depjob.remaining
            done = depjob.done()
            if done:
                self.status = depjob.status
            self.save()
            return done

        logger.debug("%s.done: %s" % (str(self), self.status))
        return self.status == Job.COMPLETE or self.status == Job.ERROR

    def datafile(self):
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)
    
    def data(self):
        if os.path.exists(self.datafile()):
            f = open(self.datafile(), "r")
            reportdata = pickle.load(f)
            f.close()
        else:
            reportdata = None

        return reportdata

    def save(self):
        self.handle = self.compute_handle()
        super(Job, self).save()
        
    def savedata(self, data):
        logger.debug("Job %s (table %s) saving data to datafile %s" %
                     (str(self), str(self.table), self.datafile()))
        f = open(self.datafile(), "w")
        pickle.dump(data, f)
        f.close()
        logger.debug("Job %s (table %s) data saved" %
                     (str(self), str(self.table)))

    def pandas_dataframe(self):
        data = self.data()
        if len(data) == 0:
            # Empty dataframe
            frame = None
        else:
            frame = pandas.DataFrame(self.data(),
                                     columns=[col.name for col in self.table.get_columns()])

        return frame
        
    def export_sqlite(self, dbfilename, tablename=None):
        import sqlite3
        if tablename is None:
            tablename = "table%d" % self.table.id
        conn = sqlite3.connect(dbfilename)
        c = conn.cursor()
        dbcols = []
        for col in self.table.get_columns():
            dbcols.append("%s %s" % (col.name, "real" if col.isnumeric else "text"))

        c.execute("DROP TABLE IF EXISTS %s" % tablename)
        c.execute("CREATE TABLE %s (%s)" % (tablename, ",".join(dbcols)))

        data = self.data()
        for row in data:
            dbcols = []
            for col in row:
                if type(col) in [str, unicode]:
                    dbcols.append("'%s'" % col)
                else:
                    dbcols.append(str(col))
            c.execute("INSERT INTO %s VALUES(%s)" % (tablename, ",".join(dbcols)))
        conn.commit()
        conn.close()
        
    def json(self, data=None):
                                      
        return { 'progress': self.progress,
                 'remaining': self.remaining,
                 'status': self.status,
                 'message': self.message,
                 'data': data }

    def combine_filterexprs(self, joinstr="and"):
        exprs = []
        criteria = self.criteria
        for e in [self.table.filterexpr, criteria.filterexpr if criteria else None]:
            if e != "" and e != None:
                exprs.append(e)

        if len(exprs) > 1:
            return "(" + (") " + joinstr + " (").join(exprs) + ")"
        elif len(exprs) == 1:
            return exprs[0]
        else:
            return ""
            
    def start(self):
        ignore_cache = self.criteria.ignore_cache
        
        with lock:
            # Look for another job running
            running = self.get_depjob()
            if not running or (ignore_cache and running.status == self.COMPLETE):
                running = None
                self.status = self.RUNNING
                self.progress = 0
                self.save()
            else:
                self.status = self.RUNNING_DEP
                self.progress = running.progress
                self.save()

        # See if this job was run before and we have a valid cache file
        if running:
            logger.debug("Job %s: Shadowing a running job by the same handle: %s" %
                         (str(self), str(running)))
            
        elif os.path.exists(self.datafile()) and not ignore_cache:
            logger.debug("Job %s: results from cachefile" % str(self))
            self.status = self.COMPLETE
            self.progress = 100
            self.save()

        else:
            logger.debug("Job %s: Spawning AsyncWorker to run report" % str(self))
            # Lookup the query class for this table
            i = importlib.import_module(self.table.module)
            queryclass = i.TableQuery
            
            # Create an asynchronous worker to do the work
            worker = AsyncWorker(self, queryclass)
            worker.start()

#
# AsyncWorker
#
class AsyncWorker(threading.Thread):
    def __init__(self, job, queryclass):
        threading.Thread.__init__(self)
        self.job = job
        self.queryclass = queryclass
        
    def run(self):
        logger.debug("Starting job %s" % self.job.handle)
        job = self.job
        try:
            query = self.queryclass(self.job.table, self.job)
            query.run()
            fulldata = self.job.table.compute_synthetic(query.data)
            job.savedata(fulldata)
            #job.savedata(query.data)
            logger.debug("Saving job %s as COMPLETE" % self.job.handle)
            job.progress = 100
            job.status = job.COMPLETE
        except:
            traceback.print_exc()
            logger.error("Job %s failed: %s" % (self.job.handle, str(sys.exc_info())))
            job.status = job.ERROR
            job.progress = 100
            job.message = traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1])

        job.save()
        sys.exit(0)
