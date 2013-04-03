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

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

from libs.options import Options

from project import settings

from jsonfield import JSONField

logger = logging.getLogger(__name__)

from apps.datasource.devicemanager import DeviceManager

# Support subclassing via get_subclass()
# objects = InheritanceManager()

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
        return self.name

#
# Table
#
class Table(models.Model):
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)    # source module name
    device = models.ForeignKey(Device, null=True)
    filterexpr = models.TextField(null=True)
    duration = models.IntegerField()             # length of query in minutes
    resolution = models.IntegerField(default=60) # resolution of graph in seconds
    sortcol = models.ForeignKey('Column', null=True, related_name='Column')
    rows = models.IntegerField(default=-1)

    options = JSONField()

    def get_options(self):
        i = importlib.import_module(self.module)
        cls = i.TableOptions
        return cls.decode(json.dumps(self.options))

    def __unicode__(self):
        return "%s (id=%s)" % (self.name, str(self.id))

    def get_columns(self):
        return Column.objects.filter(table=self).order_by('position')

class Column(models.Model):

    table = models.ForeignKey(Table)
    name = models.CharField(max_length=30)
    label = models.CharField(max_length=30)
    position = models.IntegerField()
    options = JSONField()

    iskey = models.BooleanField(default=False)
    isnumeric = models.BooleanField(default=True)
    datatype = models.CharField(max_length=50, default='') # metric, bytes, time -> XXXCJ make enumeration
    units = models.CharField(max_length=50, default='') 

    def __unicode__(self):
        return self.label

    def get_options(self):
        i = importlib.import_module(self.module)
        cls = i.ColumnOptions
        return cls.decode(json.dumps(self.options))

    @classmethod
    def create(cls, table, name, label=None, datatype='', units='', iskey=False, issortcol=False):
        c = Column(table=table, name=name, label=label, datatype=datatype, units=units, iskey=iskey)
        posmax = Column.objects.filter(table=table).aggregate(Max('position'))
        c.position = posmax['position__max'] or 1
        c.save()
        if issortcol:
            table.sortcol = c
            table.save()
        
class Criteria(Options):
    def __init__(self, t0=None, t1=None, duration=None, *args, **kwargs):
        super(Criteria, self).__init__(*args, **kwargs)
        self.t0 = t0
        self.t1 = t1
        self.duration = duration

    def compute_times(self, table):
        if self.t1 is None:
            self.t1 = time.time()

        # Snap backwards based on table resolution
        self.t1 = self.t1 - self.t1 % table.resolution

        if self.t0 is None:
            if self.duration is None:
                self.duration = table.duration*60

            self.t0 = self.t1 - self.duration

        self.t0 = self.t0 - self.t0 % table.resolution
            

#
# Job
#
class Job(models.Model):

    table = models.ForeignKey(Table)
    criteria = JSONField(null=True)

    NEW = 0
    RUNNING = 1
    COMPLETE = 2
    ERROR = 3
    
    status = models.IntegerField(default=NEW,
                                 choices = ((NEW, "New"),
                                            (RUNNING, "Running"),
                                            (COMPLETE, "Complete"),
                                            (ERROR, "Error")))

    message = models.CharField(max_length=200, default="")
    progress = models.IntegerField(default=-1)
    remaining = models.IntegerField(default=-1)

    def __unicode__(self):
        return "%s, %s %s%%" % (self.table.name, self.status, self.progress)

    @property
    def handle(self):
        h = hashlib.md5()
        h.update(str(self.table.id))
        h.update('.'.join([c.name for c in self.table.get_columns()]))
        h.update(json.dumps(self.criteria))
        return h.hexdigest()
    
    def done(self):
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

    def savedata(self, data):
        f = open(self.datafile(), "w")
        pickle.dump(data, f)
        f.close()

    def pandas_dataframe(self):
        import pandas

        frame = pandas.DataFrame(self.data(),
                                 columns = [col.name for col in self.table.get_columns()])

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

    def get_criteria(self):
        c = Criteria.decode(json.dumps(self.criteria))
        return c

    def save_criteria(self, criteria):
        self.criteria = json.loads(criteria.encode())
        self.save()
        
    def start(self):
        # First, recompute the criteria times
        criteria = self.get_criteria()
        criteria.compute_times(self.table)
        self.save_criteria(criteria)
        criteria = self.get_criteria()

        # See if this job was run before and we have a valid cache file
        if os.path.exists(self.datafile()):
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
            job.savedata(query.data)
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
