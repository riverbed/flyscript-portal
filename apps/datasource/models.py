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
import pytz
import pandas

from django.db import models
from django.db.models import Max
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import F
from django.db.models.signals import pre_delete 
from django.dispatch import receiver
from django import forms

from rvbd.common.utils import DictObject

from apps.devices.models import Device
from libs.fields import PickledObjectField
from project import settings

logger = logging.getLogger(__name__)

if settings.DATABASES['default']['ENGINE'].endswith('sqlite3'):
    # sqlite doesn't support row locking (select_for_update()), so need
    # to use a threading lock.  This provides support when running
    # the dev server.  It will not work across multiple processes, only
    # between threads of a single process
    lock = threading.RLock()
else:
    lock = None

age_jobs_last_run = 0

class LocalLock(object):
    def __enter__(self):
        if lock is not None:
            lock.acquire() 

    def __exit__(self, type, value, traceback):
        if lock is not None:
            lock.release()
        return False

class TableField(models.Model):
    """ Defines a single field associated with a table.

        Primarily used to parameterize reports with values that may change
        from time to time, such as interfaces, thresholds, QOS types, etc.

        keyword  -- text name of table field or TableOption field
        template -- python string template to use for replacement, e.g.
                    'inbound interface {} and qos EF', where the {} would
                    be replaced with the value provided in the form field
        label    -- text label shown in the HTML form
        initial  -- starting or default value to include in the form

        optional:
        field_cls    -- form field class, defaults to forms.CharField.
        field_kwargs -- additional keywords to pass to field initializer
        parent       -- reference to another TableField object which
                        provides values to inherit from.  This allows
                        multiple fields to be enumerated while only
                        displaying/filling out a single form field.
                        TableField which have a parent object identified
                        will not be included in the HTML form output.
    """
    keyword = models.CharField(max_length=100)
    template = models.CharField(max_length=100)
    label = models.CharField(max_length=100)
    help_text = models.CharField(blank=True, null=True, default=None, max_length=400)
    initial = PickledObjectField(blank=True, null=True)

    field_cls = PickledObjectField(null=True)
    field_kwargs = PickledObjectField(blank=True, null=True)

    parent = models.ForeignKey("self", blank=True, null=True,
                               related_name="children")

    # whether a value must be provided by the user
    required = models.BooleanField(default=False)

    # instance placeholder for form return values, not for database storage
    value = PickledObjectField(null=True, blank=True)

    def __repr__(self):
        return "<TableField %s (%s)>" % (self.keyword, self.id)

    def __unicode__(self):
        return "<TableField %s (%s)>" % (self.keyword, self.id)

    def save(self, *args, **kwargs):
        #if not self.field_type:
        #    self.field_type = 'forms.CharField'
        super(TableField, self).save(*args, **kwargs)

    def is_report_criteria(self, table):
        """ Runs through intersections of widgets to determine if this criteria
            is applicable to the passed table

            report  <-->  widgets  <-->  table
                |
                L- TableField (self)
        """
        wset = set(table.widget_set.all())
        rset = set(self.report_set.all())
        return any(wset.intersection(set(rwset.widget_set.all())) for rwset in rset)

    @classmethod
    def find_instance(cls, key):
        """ Return instance given a keyword. """
        params = TableField.objects.filter(keyword=key)
        if len(params) == 0:
            return None
        elif len(params) > 1:
            raise KeyError("Multiple TableField matches found for %s"
                           % key)
        param = param[0]
        return param

    @classmethod
    def get_children(cls, key, value):
        """ Given a key, return all children objects
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
    duration = models.IntegerField(null=True)         # default duration in seconds
    resolution = models.IntegerField(default=60)      # query resolution, sec
    sortcol = models.ForeignKey('Column', null=True, related_name='Column')
    rows = models.IntegerField(default=-1)

    # deprecated interface for profiler key/value separated by comma
    datafilter = models.TextField(null=True, blank=True)  

    # indicator field for analysis/synthetic tables
    resample = models.BooleanField(default=False)

    # options are typically fixed attributes defined at Table creation
    options = PickledObjectField()                          

    # list of fields that must be bound to values in criteria
    # that this table needs to run
    fields = models.ManyToManyField(TableField, null=True)
    
    # indicate if data can be cached 
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
        
        posmax = Column.objects.filter(table=table).aggregate(Max('position'))
        pos = (posmax['position__max'] or 0) + 1

        for c in table.get_columns():
            if columns is not None and c.name not in columns:
                continue
            if except_columns is not None and c.name in except_columns:
                continue
            issortcol = (c == c.table.sortcol)
            c.pk = None
            c.table = self
            c.position = pos
            pos = pos + 1
            c.save()
            if issortcol:
                self.sortcol = c
                self.save()

    def apply_table_criteria(self, criteria):
        """ Merge updates from dict of passed criteria values

            Changes are only applied to instance, not saved to database
        """
        # XXXCJ - needs to be revamped
        return
    
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
        c.position = (posmax['position__max'] or 0) + 1
        c.save()
        if issortcol:
            table.sortcol = c
            table.save()
        return c


class Criteria(DictObject):
    """ Manage a collection of criteria values. """
    def __init__(self, **kwargs):
        """ Initialize a criteria object based on key/value pairs. """

        self.starttime = None
        self.endtime = None
        self.duration = None

        super(Criteria, self).__init__(kwargs)

        #self.filterexpr = filterexpr
        #self.ignore_cache = ignore_cache

        # Keep track of the original starttime / endtime
        # This are needed when recomputing start/end times with
        # different default durations
        self._orig_starttime = self.starttime
        self._orig_endtime = self.endtime
        self._orig_duration = self.duration

    def __setattr__(self, key, value):
        self[key] = value
        if key.startswith('_'):
            return
        elif key in ['starttime', 'endtime', 'duration']:
            self['_orig_%s' % key] = value
        else:
            param = TableField.find_instance(key)
            if param.initial != value:
                param.initial = value
                param.save()
            
    def print_details(self):
        """ Return instance variables as nicely formatted string
        """
        return ', '.join([("%s: %s" % (k,v)) for k,v in self.iteritems()])

    def build_for_table(self, table):
        """ Build a criteria object for a table.

        This copies over all criteria parameters but has 
        special handling for starttime, endtime, and duration,
        as they may be altered if duration is 'default'.

        """
        crit = Criteria(starttime=self._orig_starttime,
                         endtime=self._orig_endtime,
                         duration=self._orig_duration)

        for k,v in self.iteritems():
            if (  (k in ['starttime', 'endtime', 'duration']) or
                  k.startswith('_')):
                continue
            
            crit[k] = v

        return crit
                        
    def compute_times(self, default_duration=None):
        # Start with the original values not any values formerly computed
        duration = self._orig_duration or default_duration
        starttime = self._orig_starttime
        endtime = self._orig_endtime

        if starttime is not None:
            if endtime is not None:
                duration = endtime - starttime
            elif duration is not None:
                endtime = starttime + duration
            else:
                raise ValueError("Cannot compute times, have starttime but not endtime or duration")
            
        elif endtime is None:
            endtime = datetime.datetime.now()
            
        if duration is not None:
            starttime = endtime - duration
        else:
            raise ValueError("Cannot compute times, have endtime but not starttime or duration")

        self.duration = duration
        self.starttime = starttime
        self.endtime = endtime
        
class Job(models.Model):

    # Timestamp when the job was created
    created = models.DateTimeField(auto_now_add=True)

    # Timestamp the last time the job was accessed
    touched = models.DateTimeField(auto_now_add=True)

    # Number of references to this job
    refcount = models.IntegerField(default=0)

    # Whether this job is a child of another job
    ischild = models.BooleanField(default=False)

    # If ischild, this points to the parent job
    parent = models.ForeignKey('self', null=True)

    # Table assocaited with this job
    table = models.ForeignKey(Table)

    # Criteria used to start this job - an instance of the Criteria class
    criteria = PickledObjectField(null=True)

    # Actual criteria as returned by the job after running
    actual_criteria = PickledObjectField(null=True)

    # Unique handle for the job
    handle = models.CharField(max_length=100, default="")

    # Job status
    NEW = 0
    RUNNING = 1
    COMPLETE = 3
    ERROR = 4
    
    status = models.IntegerField(
        default=NEW,
        choices=((NEW, "New"),
                 (RUNNING, "Running"),
                 (COMPLETE, "Complete"),
                 (ERROR, "Error")))

    # Message if job complete or error
    message = models.CharField(max_length=200, default="")

    # While RUNNING, this provides an indicator of progress 0-100
    progress = models.IntegerField(default=-1)

    # While RUNNING, time remaining
    remaining = models.IntegerField(default=None, null=True)

    def __unicode__(self):
        if self.handle == '':
            return "<Job %s t=%s>" % (self.id, self.table.id)
        else:
            return "<Job %s t=%s %8.8s>" % (self.id, self.table.id, self.handle)
    
    def refresh(self):
        """ Refresh dynamic job parameters from the database. """
        job = Job.objects.get(pk=self.pk)
        for k in ['status', 'message', 'progress', 'remaining',
                  'actual_criteria', 'touched', 'refcount']:
            setattr(self, k, getattr(job, k))
    
    @transaction.commit_on_success
    def safe_update(self, **kwargs):
        """ Update the job with the passed dictionary in a database safe way.

        This method updates only the requested paraemters and refreshes
        the rest from the database.  This should be used for all updates
        to Job's to ensure that unmodified keys are not accidentally
        clobbered by doing a blanket job.save().

        """
    
        if kwargs is None:
            return

        with LocalLock():
            logger.debug("%s safe_update %s" % (self, kwargs))
            Job.objects.filter(pk=self.pk).update(**kwargs)

            # Force a reload of the job to get latest data
            self.refresh()

            if not self.ischild:
                # Push changes to children of this job
                child_kwargs = {}
                for k,v in kwargs.iteritems():
                    if k in ['status', 'message', 'progress', 'remaining',
                             'actual_criteria']:
                        child_kwargs[k] = v
                # There should be no recursion, so a direct update to the database
                # is possible.  (If recursion, would need to call self_update()
                # on each child.)
                Job.objects.filter(parent=self).update(**child_kwargs)
            
    @classmethod
    def create(cls, table, criteria):

        with LocalLock():
            with transaction.commit_on_success():
                # Lockdown start/endtimes
                try:
                    logger.debug("table.duration: %s - %s" % (table, table.duration))
                    default_duration = (None if not table.duration else
                                        datetime.timedelta(seconds=table.duration))
                    criteria.compute_times(default_duration)
                except ValueError:
                    # Ignore errors, this table may not have start/end times
                    pass
                
                # Compute the handle -- this will take into account cacheability
                handle = Job._compute_handle(table, criteria)

                # Look for another job by the same handle in any state except ERROR
                if not criteria.ignore_cache:
                    parents = (Job.objects
                               .select_for_update()
                               .filter(status__in=[Job.NEW, Job.COMPLETE, Job.RUNNING],
                                       handle=handle,
                                       ischild=False)
                               .order_by('created'))

                    logger.debug("%s just finished parents query" % str(handle))
                    time.sleep(0.2)
                else:
                    parents = None

                if parents is not None and len(parents) > 0:
                    parent = parents[0]

                    job = Job(table = table,
                              criteria = criteria,
                              status = parent.status,
                              handle = handle,
                              parent = parent,
                              ischild = True,
                              progress = parent.progress,
                              remaining = parent.remaining,
                              message = '')
                    job.save()

                    parent.reference("Link from job %s" % (job))
                    parent.safe_update(touched = datetime.datetime.utcnow())

                    logger.info("%s: New job for table %s, linked to parent %s" %
                                (job, table.name, parent))
                else:
                    job = Job(table = table,
                              criteria = criteria,
                              status = Job.NEW,
                              handle = handle,
                              parent = None,
                              ischild = False,
                              progress = 0,
                              remaining = -1,
                              message = '')
                    job.save()
                    logger.info("%s: New job for table %s" % (job, table.name))

            # Flush old jobs
            Job.age_jobs()

        return job
    
    def __unicode__(self):
        return "<Job %s (%8.8s) - t%s>" % (self.id, self.handle, self.table.id)
    
    @classmethod
    def _compute_handle(cls, table, criteria):
        h = hashlib.md5()
        h.update(str(table.id))

        if table.cacheable and not criteria.ignore_cache:
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
            h.update('.'.join([c.name for c in table.get_columns(ephemeral=False)]))
            for k, v in criteria.iteritems():
                #logger.debug("Updating hash from %s -> %s" % (k,v))
                h.update('%s:%s' % (k, v))
        else:
            # Table is not cacheable, instead use current time plus a random value
            # just to get a unique hash
            h.update(str(datetime.datetime.now()))
            h.update(str(random.randint(0,10000000)))

        return h.hexdigest()

    def reference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount')+1)
        logger.debug("%s: reference(%s) @ %d" %
                     (self, message, Job.objects.get(pk=pk).refcount))
        
    def dereference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount')-1)
        logger.debug("%s: dereference(%s) @ %d" %
                     (self, message, Job.objects.get(pk=pk).refcount))
        
    def json(self, data=None):
        """ Return a simple JSON structure representing the status of this Job """
        self.refresh()
        return {'id': self.id,
                'handle': self.handle,
                'progress': self.progress,
                'remaining': self.remaining,
                'status': self.status,
                'message': self.message,
                'data': data}

    def combine_filterexprs(self, joinstr="and", exprs=None):
        self.refresh()

        criteria = self.criteria
        if exprs is None:
            exprs = []
        elif type(exprs) is not list:
            exprs = [exprs]
            
        exprs.append(self.table.filterexpr)

        nonnull_exprs = []
        for e in exprs:
            if e != "" and e is not None:
                nonnull_exprs.append(e)

        if len(nonnull_exprs) > 1:
            return "(" + (") " + joinstr + " (").join(nonnull_exprs) + ")"
        elif len(nonnull_exprs) == 1:
            return nonnull_exprs[0]
        else:
            return ""

    def start(self):
        """ Start this job. """

        self.refresh()

        if self.ischild:
            logger.debug("%s: Shadowing parent job %s" % (self, self.parent))
            return
        
        with transaction.commit_on_success():
            logger.debug("%s: Starting job" % str(self))
            
            if self.table.device and not self.table.device.enabled:
                # User has disabled the device so lets wrap up here
                
                # would be better if we could mark COMPLETE vs ERROR, but then follow-up
                # processing would occur which we want to avoid.  This short-circuits the
                # process to return the message in the Widget window immediately.
                logger.debug("%s: Device %s disabled, bypassing job" % (self, self.table.device))
                self.mark_error('Device %s disabled.\n'
                                'See Configure->Edit Devices page to enable.'
                                % self.table.device.name)
            else:
                self.mark_progress(0)

                logger.debug("%s: Spawning AsyncWorker to run report" % str(self))
                # Lookup the query class for this table
                i = importlib.import_module(self.table.module)
                queryclass = i.TableQuery

                # Create an asynchronous worker to do the work
                worker = AsyncWorker(self, queryclass)
                worker.start()

    def mark_error(self, message):
        logger.warning("%s failed: %s" % (self, message))
        self.safe_update(status = Job.ERROR,
                         progress = 100,
                         message = message)

    def mark_complete(self):
        logger.info("%s complete" % (self))
        self.safe_update(status = Job.COMPLETE,
                         progress = 100,
                         message = '')

    def mark_progress(self, progress, remaining=None):
        logger.debug("%s progress %s" % (self, progress))
        self.safe_update(status = Job.RUNNING,
                         progress = progress,
                         remaining = remaining)


    def datafile(self):
        """ Return the data file for this job. """
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)
    
    def data(self):
        """ Returns a pandas.DataFrame of the data, or None if not available. """

        with transaction.commit_on_success():
            self.refresh()
            if not self.status == Job.COMPLETE:
                raise ValueError("Job not complete, no data available")
            
            self.reference("data()")

            e = None
            try:
                logger.debug("%s looking for data file: %s" % (str(self), self.datafile()))
                if os.path.exists(self.datafile()):
                    df = pandas.load(self.datafile())
                    logger.debug("%s data loaded %d rows from file: %s" % (str(self), len(df), self.datafile()))
                else:
                    logger.debug("%s no data, missing data file: %s" % (str(self), self.datafile()))
                    df = None
            except Exception as e:
                pass
            finally:
                self.dereference("data()")

            if e:
                raise e
            
            return df

    def values(self):
        """ Return data as a list of lists. """

        df = self.data()
        if df is not None:
            # Replace NaN with None
            df = df.where(pandas.notnull(df), None)
            
            # Extract tha values in the right order
            all_columns = self.table.get_columns()
            all_col_names = [c.name for c in all_columns]
            vals = df.ix[:, all_col_names].values.tolist()
        else:
            vals = []
        return vals
        
    @classmethod
    def age_jobs(cls, old=None, ancient=None, force=False):
        """ Delete old jobs that have no refcount and all ancient jobs. """
        # Throttle - only run this at most once every 15 minutes
        global age_jobs_last_run
        if not force and time.time() - age_jobs_last_run < 60*15:
            return
        
        if old is None:
            old = datetime.timedelta(seconds=settings.APPS_DATASOURCE['job_age_old_seconds'])
        elif type(old) in [int, float]:
            old = datetime.timedelta(seconds=old)
            
        if ancient is None:
            ancient = datetime.timedelta(seconds=settings.APPS_DATASOURCE['job_age_ancient_seconds'])
        elif type(ancient) in [int, float]:
            ancient = datetime.timedelta(seconds=ancient)

        # Ancient jobs are deleted regardless of refcount
        now = datetime.datetime.now(tz=pytz.utc)
        (Job.objects.filter(touched__lte = now - ancient)).delete()
            
        # Old jobs are deleted only if they have a refcount of 0
        (Job.objects.filter(touched__lte = now - old, refcount=0)).delete()

        age_jobs_last_run = time.time()

    def done(self):
        self.refresh()
        logger.debug("%s status: %s - %s%%" % (str(self), self.status, self.progress))
        return self.status == Job.COMPLETE or self.status == Job.ERROR

@receiver(pre_delete, sender=Job)
def _my_job_delete(sender, instance, **kwargs):
    if instance.parent is not None:
        instance.parent.dereference(str(instance))
        
class AsyncWorker(threading.Thread):
    def __init__(self, job, queryclass):
        threading.Thread.__init__(self)
        self.job = job
        self.queryclass = queryclass

        logger.info("%s created" % self)
        job.reference("AsyncWorker created")

    def __delete__(self):
        if self.job:
            self.job.dereference("AsyncWorker deleted")
            
    def __unicode__(self):
        return "<AsyncWorker %s>" % (self.job)

    def __str__(self):
        return "<AsyncWorker %s>" % (self.job)

    def run(self):
        job = self.job
        try:
            logger.info("%s running queryclass %s" % (self, self.queryclass))
            query = self.queryclass(job.table, job)
            if query.run():
                logger.info("%s query finished" % self)
                if isinstance(query.data, list) and len(query.data) > 0:
                    # Convert the result to a dataframe
                    columns = [col.name for col in
                               job.table.get_columns(synthetic=False)]
                    df = pandas.DataFrame(query.data, columns=columns)
                    for col in job.table.get_columns(synthetic=False):
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

                elif ((query.data is None) or
                      (isinstance (query.data, list) and len(query.data) == 0)):
                    df = None
                elif isinstance(query.data, pandas.DataFrame):
                    df = query.data
                else:
                    raise ValueError("Unrecognized query result type: %s" % type(query.data))

                if df is not None:
                    df = job.table.compute_synthetic(df)

                if df is not None:
                    df.save(job.datafile())
                    logger.debug("%s data saved to file: %s" % (str(self), job.datafile()))
                else:
                    logger.debug("%s no data saved, data is empty" % (str(self)))

                logger.info("%s finished as COMPLETE" % self)
                job.mark_complete()
            else:
                # If the query.run() function returns false, the run() may
                # have set the job.status, check and update if not
                vals = {}
                job.refresh()
                if not job.done():
                    vals['status'] = job.ERROR
                if job.message == "":
                    vals['message'] = "Query returned an unknown error"
                vals['progress'] = 100
                job.safe_update(**vals)
                logger.error("%s finished with an error: %s" % (self, job.message))
                
        except:
            traceback.print_exc()
            logger.error("%s raised an exception: %s" % (self, str(sys.exc_info())))
            job.safe_update(status = job.ERROR,
                            progress = 100,
                            message = traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))

        finally:
            job.dereference("AsyncWorker exiting")
            
        logger.debug("AsyncWorker caling sys.exit(0)")
        sys.exit(0)

class BatchJobRunner(object):

    def __init__(self, basejob, batchsize=4, min_progress=0, max_progress=100):
        self.basejob = basejob
        self.jobs = []
        self.batchsize = batchsize
        self.min_progress = min_progress
        self.max_progress = max_progress

    def add_job(self, job):
        self.jobs.append(job)

    def run(self):
        jobs = self.jobs

        for i in range(0, len(jobs), self.batchsize):
            batch = jobs[i:i+self.batchsize]
            batch_status = {}
            for job in batch:
                batch_status[job.id] = False
                job.start()

            interval = 0.2
            max_interval = 2
            batch_done = False
            while not batch_done:
                batch_progress = 0
                batch_done = True
                for job in batch:
                    job.refresh()
                    
                    if batch_status[job.id] is False:
                        if job.done():
                            batch_status[job.id] = True
                        else:
                            batch_done = False
                            batch_progress += (float(job.progress) / float(self.batchsize))
                    else:
                        batch_progress += (100.0 / float(self.batchsize))

                total_progress = (i * 100.0 + batch_progress * self.batchsize) / len(jobs)
                job_progress = (self.min_progress +
                                (total_progress * (self.max_progress -
                                                   self.min_progress)) / 100)
                logger.debug("BatchJobRunner: batch[%d:%d] %d%% / total %d%% / job %d%%",
                             i, i+self.batchsize, int(batch_progress),
                             int(total_progress), int(job_progress))
                self.basejob.mark_progress(job_progress)
                if not batch_done:
                    time.sleep(interval)
                    interval = (interval * 2) if interval < max_interval else max_interval

                
