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
import numpy

from django.db import models
from django.core.exceptions import ObjectDoesNotExist

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
    filterexpr = models.TextField(blank=True)
    duration = models.IntegerField()             # length of query in minutes
    resolution = models.IntegerField(default=60) # resolution of graph in seconds
    sortcol = models.ForeignKey('Column', null=True, related_name='Column')
    rows = models.IntegerField(default=-1)

    options = JSONField()

    def get_options(self):
        import apps.datasource.modules
        cls = apps.datasource.modules.__dict__[self.module].TableOptions
        return cls.decode(json.dumps(self.options))

    def __unicode__(self):
        return str(self.id)

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
        import apps.datasource.modules
        cls = apps.datasource.modules.__dict__[self.table.module].ColumnOptions
        return cls.decode(json.dumps(self.options))

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
        return self.table.id
    
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

    def start(self):
        # Lookup the query class for this table
        import apps.datasource.modules
        queryclass = apps.datasource.modules.__dict__[self.table.module].TableQuery

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
