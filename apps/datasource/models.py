# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#  https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import sys
import pickle
import logging
import traceback
import threading
import time
import hashlib
import importlib
import tokenize
from StringIO import StringIO
import random
import datetime

import pandas
from django.db import models
from django.db.models import Max
from rvbd.common.utils import DictObject

from apps.devices.models import Device
from libs.fields import PickledObjectField
from project import settings


logger = logging.getLogger(__name__)

lock = threading.Lock()


class TableCriteria(models.Model):
    """ Criteria model to provide report run-time overrides for key values.

        Primarily used to parameterize reports with values that may change
        from time to time, such as interfaces, thresholds, QOS types, etc.

        keyword  -- text name of table field or TableOption field
        template -- python string template to use for replacement, e.g.
                    "inbound interface {} and qos EF", where the {} would
                    be replaced with the value provided in the form field
        label    -- text label shown in the HTML form
        initial  -- starting or default value to include in the form

        optional:
        field_type   -- text name of form field type, defaults to
                        `forms.CharField`.
        field_kwargs -- additional keywords to pass to field initializer
        parent       -- reference to another TableCriteria object which
                        provides values to inherit from.  This allows
                        multiple criteria to be enumerated while only
                        displaying/filling out a single form field.
                        TableCriteria which have a parent object identified
                        will not be included in the HTML form output.
    """
    keyword = models.CharField(max_length=100)
    template = models.CharField(max_length=100)
    label = models.CharField(max_length=100)

    initial = PickledObjectField(blank=True, null=True)

    field_type = models.CharField(max_length=100, default='forms.CharField')
    field_kwargs = PickledObjectField(blank=True, null=True)

    parent = models.ForeignKey("self", blank=True, null=True,
                               related_name="children")

    # whether a value must be provided by the user
    required = models.BooleanField(default=False)

    # instance placeholder for form return values, not for database storage
    value = PickledObjectField(null=True, blank=True)

    def __unicode__(self):
        return "<TableCriteria %s (id=%s)>" % (self.keyword, str(self.id))

    def save(self, *args, **kwargs):
        #if not self.field_type:
        #    self.field_type = 'forms.CharField'
        super(TableCriteria, self).save(*args, **kwargs)

    def is_report_criteria(self, table):
        """ Runs through intersections of widgets to determine if this criteria
            is applicable to the passed table

            report  <-->  widgets  <-->  table
                |
                L- TableCriteria (self)
        """
        wset = set(table.widget_set.all())
        rset = set(self.report_set.all())
        return any(wset.intersection(set(rwset.widget_set.all())) for rwset in rset)

    @classmethod
    def get_instance(cls, key, value):
        """ Return instance given the 'criteria_%d' formatted key

            If we have an initial value (e.g. no parent specified)
            then save value as our new initial value
        """
        tc = TableCriteria.objects.get(pk=key.split('_')[1])
        if tc.initial and tc.initial != value:
            tc.initial = value
            tc.save()
        tc.value = value
        return tc

    @classmethod
    def get_children(cls, key, value):
        """ Given a 'criteria_%d' key, return all children objects
            with value attributes filled in.  Return empty list if no
            children.
        """
        parent = cls.get_instance(key, value)
        children = parent.children.all()
        for c in children:
            c.value = value
        return children


class Table(models.Model):
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)         # source module name
    device = models.ForeignKey(Device, null=True, on_delete=models.SET_NULL)
    filterexpr = models.TextField(null=True)
    duration = models.IntegerField(null=True)         # length of query, mins
    resolution = models.IntegerField(default=60)      # query resolution, sec
    sortcol = models.ForeignKey('Column', null=True, related_name='Column')
    rows = models.IntegerField(default=-1)

    # deprecated interface for profiler key/value separated by comma
    datafilter = models.TextField(null=True, blank=True)  

    # indicator field for analysis/synthetic tables
    resample = models.BooleanField(default=False)

    # options are typically fixed attributes defined at Table creation
    options = PickledObjectField()                          

    # criteria are used to override instance values at run time
    criteria = models.ManyToManyField(TableCriteria, null=True)
    
    # indicate if data can be cached based on criteria
    cacheable = models.BooleanField(default=True)

    @classmethod
    def create(cls, name, module, **kwargs):
        t = Table(name=name, module=module, **kwargs)
        t.save()
        return t
    
    def __unicode__(self):
        return "<Table %s (%s)>" % (str(self.id), self.name)

    def get_columns(self, synthetic=None, ephemeral=None, iskey=None):
        """
        Return the list of columns for this table.

        `synthetic` is tri-state: None (default) is don't care,
            True means only synthetic columns, False means
            only non-synthetic columns

        `ephemeral` is tri-state: None (default) is don't care,
            True means only ephemeral columns, False means
            only non-ephemeral columns

        `iskey` is tri-state: None (default) is don't care,
            True means only key columns, False means
            only non-key columns

        """
        
        filtered = []
        for c in Column.objects.filter(table=self).order_by('position'):
            if synthetic is not None and c.synthetic != synthetic:
                continue
            if ephemeral is not None and c.ephemeral != ephemeral:
                continue
            if iskey is not None and c.iskey != iskey:
                continue
            filtered.append(c)
            
        return filtered

    def copy_columns(self, table, columns=None, except_columns=None):
        """ Copy the columns from `table` into this table.

        This method will copy all the columsn from another table, including
        all attributes as well as sorting.

        """
        
        for c in table.get_columns():
            if columns is not None and c.name not in columns:
                continue
            if except_columns is not None and c.name in except_columns:
                continue
            issortcol = (c == c.table.sortcol)
            c.pk = None
            c.table = self
            c.save()
            if issortcol:
                self.sortcol = c
                self.save()

    def apply_table_criteria(self, criteria):
        """ Merge updates from dict of passed criteria values

            Changes are only applied to instance, not saved to database
        """
        for k, v in criteria.iteritems():
            if k.startswith('criteria_') and (self in v.table_set.all() or
                                              v.is_report_criteria(self)):
                replacement = v.template.format(v.value)

                if hasattr(self, v.keyword):
                    msg = 'In table %s, replacing %s with %s'
                    logger.debug(msg % (self, v.keyword, replacement))
                    setattr(self, v.keyword, replacement)

                elif hasattr(self.options, v.keyword):
                    msg = 'In table %s options, replacing %s with %s'
                    logger.debug(msg % (self, v.keyword, replacement))
                    setattr(self.options, v.keyword, replacement)

                else:
                    msg = 'WARNING: keyword %s not found in table %s or its options'
                    logger.debug(msg % (v.keyword, self))

    def compute_synthetic(self, df):
        """ Compute the synthetic columns from DF a two-dimensional array
            of the non-synthetic columns.

            Synthesis occurs as follows:

            1. Compute all synthetic columns where compute_post_resample is False

            2. If the table is a time-based table with a defined resolution, the
               result is resampled.

            3. Any remaining columns are computed.
        """
        if df is None:
            return None
        
        all_columns = self.get_columns()
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
                how[k] = colmap[k].resample_operation

            indexed = df.set_index(timecol)
            resampled = indexed.resample('%ss' % self.resolution, how).reset_index()
            df = resampled

        # 3. Compute remaining synthetic columns (post_resample is True)
        compute(df, [col for col in all_columns if (col.synthetic and
                                                    col.compute_post_resample is True)])

        return df


class Column(models.Model):

    table = models.ForeignKey(Table)
    name = models.CharField(max_length=30)
    label = models.CharField(max_length=30, null=True)
    position = models.IntegerField()
    options = PickledObjectField()

    iskey = models.BooleanField(default=False)
    isnumeric = models.BooleanField(default=True)

    synthetic = models.BooleanField(default=False)

    # Ephemeral columns are columns added to a table at run-time
    ephemeral = models.BooleanField(default=False)

    compute_post_resample = models.BooleanField(default=False)
    compute_expression = models.CharField(max_length=300)
    resample_operation = models.CharField(max_length=300, default='sum')
    
    # datatype should be an enumeration: metric, bytes, time  XXXCJ make enumeration
    datatype = models.CharField(max_length=50, default='')

    units = models.CharField(max_length=50, default='') 

    def __unicode__(self):
        return self.label

    def save(self, *args, **kwargs):
        if self.label is None:
            self.label = self.name
        super(Column, self).save()

    @classmethod
    def create(cls, table, name, label=None, datatype='', units='',
               iskey=False, issortcol=False, options=None, **kwargs):

        if len(Column.objects.filter(table=table, name=name)) > 0:
            raise ValueError("Column %s already in use for table %s" % (name, str(table)))
            
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
    def __init__(self, starttime=None, endtime=None, duration=None, 
                 filterexpr=None, table=None, ignore_cache=False, *args, **kwargs):
        super(Criteria, self).__init__(*args, **kwargs)
        self.starttime = starttime
        self.endtime = endtime
        self.duration = duration
        self.filterexpr = filterexpr
        self.ignore_cache = ignore_cache

        self._orig_starttime = starttime
        self._orig_endtime = endtime
        self._orig_duration = duration
        
        if table:
            self.compute_times(table)
            
    def print_details(self):
        """ Return instance variables as nicely formatted string
        """
        msg = 'starttime: %s, endtime: %s, duration: %s, ' % (str(self.starttime), 
                                                              str(self.endtime), 
                                                              str(self.duration))
        msg += 'filterexpr: %s, ignore_cache: %s' % (str(self.filterexpr),
                                                     str(self.ignore_cache))
        return msg

    def build_for_table(self, table):
        # used by Analysis datasource module
        crit =  Criteria(starttime=self._orig_starttime,
                         endtime=self._orig_endtime,
                         duration=self._orig_duration,
                         filterexpr=self.filterexpr,
                         ignore_cache=self.ignore_cache,
                         table=table)

        for k,v in self.iteritems():
            if k.startswith('criteria_'):
                crit[k] = v

        return crit
                        
    def compute_times(self, table):
        if table.duration is None:
            return
        
        if self.endtime is None:
            self.endtime = time.time()

        # Snap backwards based on table resolution
        self.endtime = self.endtime - self.endtime % table.resolution

        if self.starttime is None:
            if self.duration is None:
                self.duration = table.duration * 60

            self.starttime = self.endtime - self.duration

        self.starttime = self.starttime - self.starttime % table.resolution
            
    def lookup(self, key):
        """ Lookup a criteria entry by `key`. """
        if key in self:
            return self[key]
        
        for k, v in self.iteritems():
            if not k.startswith('criteria_'): continue
        
            if v.keyword == key:
                return v.value

        raise KeyError("No such criteria key '%s'" % key)

class Job(models.Model):

    table = models.ForeignKey(Table)
    criteria = PickledObjectField(null=True)
    actual_criteria = PickledObjectField(null=True)
    handle = models.CharField(max_length=100, default="")

    NEW = 0
    RUNNING = 1
    RUNNING_DEP = 2
    COMPLETE = 3
    ERROR = 4
    
    status = models.IntegerField(
        default=NEW,
        choices=((NEW, "New"),
                 (RUNNING, "Running"),
                 (RUNNING_DEP, "Running dependent on another job"),
                 (COMPLETE, "Complete"),
                 (ERROR, "Error")))

    message = models.CharField(max_length=200, default="")
    progress = models.IntegerField(default=-1)
    remaining = models.IntegerField(default=-1)

    def __unicode__(self):
        if self.handle == '':
            return "<Job t=%s>" % (self.table.id)
        else:
            return "<Job t=%s %8.8s>" % (self.table.id, self.handle)
    
    def delete(self):
        logger.debug('%s deleted' % str(self))
        super(Job, self).delete()

    def save(self, *args, **kwargs):
        """ Model save. """
        if self.handle == "":
            # Only compute the handle if it was not previously computed -- as it
            # may change if the associated table is not cacheable
            self.handle = self.compute_handle()
        super(Job, self).save(*args, **kwargs)

    def compute_handle(self):
        h = hashlib.md5()
        h.update(str(self.table.id))

        if self.table.cacheable:
            # XXXCJ - Drop ephemeral columns when computing the cache handle, since
            # the list of columns is modifed at run time.   Typical use case
            # is an analysis table which creates a time-series graph of the
            # top 10 hosts -- one column per host.  The host columns will change
            # based on the run of the dependent table.
            #
            # Including epheremal columns causes some problems because the handle is computed
            # before the query is actually run, so it never matches.
            #
            # May want to dig in to this further and make sure this doesn't pick up cache
            # files when we don't want it to
            logger.debug("%s: %s is cacheable, computing handle from criteria" % (self, str(self.table)))
            h.update('.'.join([c.name for c in self.table.get_columns(ephemeral=False)]))
            for k, v in self.criteria.iteritems():
                if not k.startswith('criteria_'):
                    #logger.debug("Updating hash from %s -> %s" % (k,v))
                    h.update('%s:%s' % (k, v))
        else:
            # Table is not cacheable, instead use current time plus a random value
            # just to get a unique hash
            logger.debug("%s: %s is not cacheable, computing unique handle" % (self, str(self.table)))
            h.update(str(datetime.datetime.now()))
            h.update(str(random.randint(0,10000000)))

        logger.info("%s: %s -> full handle: %s" % (str(self), str(self.table), h.hexdigest()))
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
                raise ValueError("%s: failed to find dependent job" % str(self))
            self.progress = depjob.progress
            self.message = depjob.message
            self.remaining = depjob.remaining
            done = depjob.done()
            if done:
                self.status = depjob.status
            self.save()
            #logger.debug("%s status: %s (from dependent %s)" % (str(self), self.status, str(depjob)))
            return done

        #logger.debug("%s status: %s" % (str(self), self.status))
        return self.status == Job.COMPLETE or self.status == Job.ERROR

    def values(self):
        """ Return data as a list of lists. """

        df = self.data()
        all_columns = self.table.get_columns()
        all_col_names = [c.name for c in all_columns]
        if df is not None:
            # Replace NaN with None
            df = df.where(pandas.notnull(df), None)
            
            # Extract tha values in the right order
            vals = df.ix[:, all_col_names].values.tolist()
        else:
            vals = []
        return vals
        
    def datafile(self):
        """ Return the data file for this job. """
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)
    
    def savedata(self, data):
        """ Save pandas DataFrame. """
        logger.debug("%s saving data to datafile %s" %
                     (str(self), self.datafile()))

        if data is not None:
            data.save(self.datafile())
            logger.debug("%s data saved to file: %s" % (str(self), self.datafile()))
        else:
            logger.debug("%s no data saved, data is empty" % (str(self)))

    def data(self):
        """ Returns a pandas.DataFrame of the data, or None if not available. """
        if os.path.exists(self.datafile()):
            df = pandas.load(self.datafile())
            logger.debug("%s data loaded %d rows from file: %s" % (str(self), len(df), self.datafile()))
        else:
            logger.debug("%s no data, missing data file: %s" % (str(self), self.datafile()))
            df = None

        return df

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
        raise Exception("Not supported.")
        # Code below no longer works -- needs to handle a DataFrame, not raw data
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
        """ Return a simple JSON structure representing the status of this Job """
        return {'id': self.id,
                'handle': self.handle,
                'progress': self.progress,
                'remaining': self.remaining,
                'status': self.status,
                'message': self.message,
                'data': data}

    def combine_filterexprs(self, joinstr="and"):
        exprs = []
        criteria = self.criteria
        for e in [self.table.filterexpr, criteria.filterexpr if criteria else None]:
            if e != "" and e is not None:
                exprs.append(e)

        if len(exprs) > 1:
            return "(" + (") " + joinstr + " (").join(exprs) + ")"
        elif len(exprs) == 1:
            return exprs[0]
        else:
            return ""
            
    def start(self):
        """ Start this job. """
        
        ignore_cache = self.criteria.ignore_cache
        
        with lock:
            # Look for another job that matches this handle
            running = self.get_depjob()
            if (  not running or

                  # ignoring cache and the job is not running -- this
                  # tries to capture the case where one report has
                  # multiple jobs based of the same base job... incomplete
                  # solution, really need to track a "run id" or something
                  (ignore_cache and running.status == self.COMPLETE) or

                  # Don't shadow failed jobs
                  (running.status == self.ERROR)):
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

        elif self.table.device and not self.table.device.enabled:
            # User has disabled the device so lets wrap up here

            # would be better if we could mark COMPLETE vs ERROR, but then follow-up
            # processing would occur which we want to avoid.  This short-circuits the
            # process to return the message in the Widget window immediately.
            logger.debug("Job %s: Device disabled, bypassing job" % str(self))
            self.status = self.ERROR
            self.message = ('Device %s disabled.\n'
                            'See Configure->Edit Devices page to enable.'
                            % self.table.device.name)
            self.progress = 100
            self.save()

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

    def mark_failed(self, message):
        logger.warning("%s failed: %s" % (self, message))
        self.status = Job.ERROR
        self.progress = 100
        self.message = message
        self.save()

class AsyncWorker(threading.Thread):
    def __init__(self, job, queryclass):
        threading.Thread.__init__(self)
        self.job = job
        self.queryclass = queryclass
        logger.info("%s created" % self)

    def __unicode__(self):
        return "<AsyncWorker %s>" % (self.job)

    def __str__(self):
        return "<AsyncWorker %s>" % (self.job)

    def run(self):
        logger.info("%s run starting" % self)
        job = self.job
        try:
            query = self.queryclass(self.job.table, self.job)
            if query.run():
                  # This log message is too verbose...
                #logger.debug("Job done, query.data: %s (%s)" % (query.data, type(query.data)))
                if isinstance(query.data, list) and len(query.data) > 0:
                    # Convert the result to a dataframe
                    columns = [col.name for col in
                               self.job.table.get_columns(synthetic=False)]
                    df = pandas.DataFrame(query.data, columns=columns)
                    for col in self.job.table.get_columns(synthetic=False):
                        s = df[col.name]
                        if col.isnumeric and s.dtype == pandas.np.dtype('object'):
                            # The column is supposed to be numeric but must have
                            # some strings.  Try replacing empty strings with NaN
                            # and see if it converts to float64
                            try:
                                df[col.name] = (s.replace('', pandas.np.NaN)
                                                .astype(pandas.np.float64))
                            except ValueError:
                                # This may incorrectly be tagged as numeric
                                pass
                    query.data = df
                elif query.data is not None and len(query.data) == 0:
                    query.data = None

                fulldata = self.job.table.compute_synthetic(query.data)
                job.savedata(fulldata)

                logger.info("%s finished as COMPLETE" % self)
                job.progress = 100
                job.status = job.COMPLETE
            else:
                # If the query.run() function returns false, the run() may
                # have set the job.status, check and update if not
                if not job.done():
                    job.status = job.ERROR
                if job.message == "":
                    job.message = ("Query returned an unknown error")
                job.progress = 100
                logger.error("%s finished with an error: %s" % (self, job.message))
                
        except:
            traceback.print_exc()
            logger.error("%s raised an exception: %s" % (self, str(sys.exc_info())))
            job.status = job.ERROR
            job.progress = 100
            job.message = traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1])

        job.save()
        sys.exit(0)
