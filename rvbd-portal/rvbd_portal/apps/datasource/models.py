# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#  https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import sys
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
import string
import pytz
import pandas
import numpy
import copy

from django.db import models
from django.db.models import Max
from django.db import transaction
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from rvbd.common.utils import DictObject
from rvbd.common import timedelta_total_seconds

from rvbd_portal.apps.datasource.exceptions import *
from rvbd_portal.libs.fields import (PickledObjectField, FunctionField,
                                     SeparatedValuesField)
from django.conf import settings


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
    """
    Defines a single field associated with a table.

    TableFields define the the parameters that are used by a Table
    at run time.  The Table.fields attribute associates one
    or more fields with the table.

    At run time, a Criteria object binds values to each field.  The
    Criteria object has an attribute matching each associated TableField
    keyword.

    When defining a TableField, the following model attributes
    may be specified:

    :param keyword: short identifier used like a variable name, this must
        be unique per table

    :param label: text label displayed in user interfaces

    :param help_text: descriptive help text associated with this field

    :param initial: starting or default value to use in user interfaces

    :param required: boolean indicating if a non-null values must be provided

    :param hidden: boolean indicating if this field should be hidden in
        user interfaces, usually true when the value is computed from
        other fields via post_process_func or post_process_template

    :param field_cls: Django Form Field class to use for rendering.
        If not specified, this defaults to CharField

    :param field_kwargs: Dictionary of additional field specific
        kwargs to pass to the field_cls constructor.

    :param parants: List of parent keywords that this field depends on
        for a final value.  Used in conjunction with either
        post_process_func or post_process_template.

    :param pre_process_func: Function to call to perform any necessary
        preprocessing before rendering a form field or accepting
        user input.

    :param post_process_func: Function to call to perform any post
        submit processing.  This may be additional value cleanup
        or computation based on other form data.

    :param post_process_template: Simple string format style template
        to fill in based on other form criteria.
    """
    keyword = models.CharField(max_length=100)
    label = models.CharField(max_length=100, null=True, default=None)
    help_text = models.CharField(blank=True, null=True, default=None, max_length=400)
    initial = PickledObjectField(blank=True, null=True)
    required = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    field_cls = PickledObjectField(null=True)
    field_kwargs = PickledObjectField(blank=True, null=True)

    parent_keywords = SeparatedValuesField(null=True)

    pre_process_func = FunctionField(null=True)
    dynamic = models.BooleanField(default=False)
    post_process_func = FunctionField(null=True)
    post_process_template = models.CharField(null=True, max_length=500)

    @classmethod
    def create(cls, keyword, label=None, obj=None, **kwargs):
        parent_keywords = kwargs.pop('parent_keywords', None)
        if parent_keywords is None:
            parent_keywords = []

        field = cls(keyword=keyword, label=label, **kwargs)
        field.save()

        if field.post_process_template is not None:
            f = string.Formatter()
            for (_, parent_keyword, _, _) in f.parse(field.post_process_template):
                if parent_keyword is not None:
                    parent_keywords.append(parent_keyword)

        field.parent_keywords = parent_keywords
        field.save()

        if obj is not None:
            obj.fields.add(field)
        return field

    def __repr__(self):
        return "<TableField %s (%s)>" % (self.keyword, self.id)

    def __unicode__(self):
        return unicode(self)

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
        param = params[0]
        return param


class Table(models.Model):
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)         # source module name
    sortcol = models.ForeignKey('Column', null=True, related_name='Column')
    rows = models.IntegerField(default=-1)
    filterexpr = models.CharField(null=True, max_length=400)

    # resample flag -- resample to the criteria.resolution
    # - this requires a "time" column
    resample = models.BooleanField(default=False)

    # options are typically fixed attributes defined at Table creation
    options = PickledObjectField()

    # list of fields that must be bound to values in criteria
    # that this table needs to run
    fields = models.ManyToManyField(TableField, null=True)

    # Default values for fields assocaited with this table, these
    # may be overridden by user criteria at run time
    criteria = PickledObjectField()

    # Function to call to tweak criteria for computing a job handle.
    # This must return a dictionary of key/value pairs of values
    # to use for computing a determining when a job must be rerun.
    criteria_handle_func = FunctionField(null=True)

    # indicate if data can be cached
    cacheable = models.BooleanField(default=True)

    @classmethod
    def create(cls, name, module, **kwargs):
        t = Table(name=name, module=module, **kwargs)
        t.save()
        return t

    def __unicode__(self):
        return "<Table %s (%s)>" % (str(self.id), self.name)

    def __repr__(self):
        return unicode(self)

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

    def compute_synthetic(self, job, df):
        """ Compute the synthetic columns from DF a two-dimensional array
            of the non-synthetic columns.

            Synthesis occurs as follows:

            1. Compute all synthetic columns where compute_post_resample
               is False

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
                            msg = "Invalid syntax, expected {name}: %s" % tvalue
                            raise ValueError(msg)
                        elif tvalue not in all_col_names:
                            raise ValueError("Invalid column name: %s" % tvalue)
                        newexpr += "df['%s']" % tvalue
                        getclose = True
                        getvalue = False
                    elif getclose:
                        if ttype != tokenize.OP and tvalue != "}":
                            msg = "Invalid syntax, expected {name}: %s" % tvalue
                            raise ValueError(msg)
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

        if self.resample:
            if timecol is None:
                raise (TableComputeSyntheticError
                       ("Table %s 'resample' is set but no 'time' column'" %
                        self))

            if (  ('resolution' not in job.criteria) and
                  ('resample_resolution' not in job.criteria)):
                raise (TableComputeSyntheticError
                       (("Table %s 'resample' is set but criteria missing " +
                         "'resolution' or 'resample_resolution'") % self))

            how = {}
            for k in df.keys():
                if k == timecol:
                    continue
                how[k] = colmap[k].resample_operation

            indexed = df.set_index(timecol)
            if 'resample_resolution' in job.criteria:
                resolution = job.criteria.resample_resolution
            else:
                resolution = job.criteria.resolution

            resolution = timedelta_total_seconds(resolution)
            if resolution < 1:
                raise (TableComputeSyntheticError
                       (("Table %s cannot resample at a resolution " +
                         "less than 1 second") % self))

            logger.debug('%s: resampling to %ss' % (self, int(resolution)))
            indexed.save('/tmp/indexed.pd')
            resampled = indexed.resample('%ss' % int(resolution), how,
                                         convention='end').reset_index()
            df = resampled

        # 3. Compute remaining synthetic columns (post_resample is True)
        compute(df, [c for c in all_columns
                     if (c.synthetic and c.compute_post_resample is True)])

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

    # datatype should be an enumeration:
    # metric, bytes, time  XXXCJ make enumeration
    datatype = models.CharField(max_length=50, default='')

    units = models.CharField(max_length=50, default='')

    def __unicode__(self):
        return self.label

    def __repr__(self):
        return unicode(self)

    def save(self, *args, **kwargs):
        if self.label is None:
            self.label = self.name
        super(Column, self).save()

    @classmethod
    def create(cls, table, name, label=None, datatype='', units='',
               iskey=False, issortcol=False, options=None, **kwargs):

        if len(Column.objects.filter(table=table, name=name)) > 0:
            raise ValueError("Column %s already in use for table %s" %
                             (name, str(table)))

        c = Column(table=table, name=name, label=label, datatype=datatype,
                   units=units, iskey=iskey, options=options, **kwargs)
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
        #else:
        #    param = TableField.find_instance(key)
        #    if param.initial != value:
        #        param.initial = value
        #        param.save()

    def print_details(self):
        """ Return instance variables as nicely formatted string
        """
        return ', '.join([("%s: %s" % (k, v)) for k, v in self.iteritems()])

    def build_for_table(self, table):
        """ Build a criteria object for a table.

        This copies over all criteria parameters but has
        special handling for starttime, endtime, and duration,
        as they may be altered if duration is 'default'.

        """
        crit = Criteria(starttime=self._orig_starttime,
                        endtime=self._orig_endtime,
                        duration=self._orig_duration)

        for k, v in self.iteritems():
            if k in ['starttime', 'endtime', 'duration'] or k.startswith('_'):
                continue

            crit[k] = v

        return crit

    def compute_times(self):
        # Start with the original values not any values formerly computed
        duration = self._orig_duration
        starttime = self._orig_starttime
        endtime = self._orig_endtime

        logger.debug("compute_times: %s %s %s" %
                     (starttime, endtime, duration))

        if starttime is not None:
            if endtime is not None:
                duration = endtime - starttime
            elif duration is not None:
                endtime = starttime + duration
            else:
                msg = ("Cannot compute times, have starttime but not "
                       "endtime or duration")
                raise ValueError(msg)

        elif endtime is None:
            endtime = datetime.datetime.now()

        if duration is not None:
            starttime = endtime - duration
        else:
            msg = ("Cannot compute times, have endtime but not "
                   "starttime or duration")
            raise ValueError(msg)

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

    # Table associated with this job
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
    message = models.TextField(default="")

    # While RUNNING, this provides an indicator of progress 0-100
    progress = models.IntegerField(default=-1)

    # While RUNNING, time remaining
    remaining = models.IntegerField(default=None, null=True)

    def __unicode__(self):
        return "<Job %s (%8.8s) - t%s>" % (self.id, self.handle, self.table.id)

    def __repr__(self):
        return unicode(self)

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
                for k, v in kwargs.iteritems():
                    if k in ['status', 'message', 'progress', 'remaining',
                             'actual_criteria']:
                        child_kwargs[k] = v
                # There should be no recursion, so a direct update to the
                # database is possible.  (If recursion, would need to call
                # self_update() on each child.)
                Job.objects.filter(parent=self).update(**child_kwargs)

    @classmethod
    def create(cls, table, criteria):

        with LocalLock():
            with transaction.commit_on_success():
                # Lockdown start/endtimes
                try:
                    criteria.compute_times()
                except ValueError:
                    # Ignore errors, this table may not have start/end times
                    pass

                # Compute the handle -- this will take into account
                # cacheability
                handle = Job._compute_handle(table, criteria)

                # Look for another job by the same handle in any state
                # except ERROR
                if not criteria.ignore_cache:
                    parents = (Job.objects
                               .select_for_update()
                               .filter(status__in=[Job.NEW,
                                                   Job.COMPLETE,
                                                   Job.RUNNING],
                                       handle=handle,
                                       ischild=False)
                               .order_by('created'))

                    logger.debug("%s just finished parents query" % str(handle))
                    time.sleep(0.2)
                else:
                    parents = None

                if parents is not None and len(parents) > 0:
                    parent = parents[0]

                    job = Job(table=table,
                              criteria=criteria,
                              actual_criteria=parent.actual_criteria,
                              status=parent.status,
                              handle=handle,
                              parent=parent,
                              ischild=True,
                              progress=parent.progress,
                              remaining=parent.remaining,
                              message='')
                    job.save()

                    parent.reference("Link from job %s" % job)
                    now = datetime.datetime.now(tz=pytz.utc)
                    parent.safe_update(touched=now)

                    logger.info("%s: New job for table %s, linked to parent %s"
                                % (job, table.name, parent))
                else:
                    job = Job(table=table,
                              criteria=criteria,
                              status=Job.NEW,
                              handle=handle,
                              parent=None,
                              ischild=False,
                              progress=0,
                              remaining=-1,
                              message='')
                    job.save()
                    logger.info("%s: New job for table %s" % (job, table.name))

                logger.debug("%s: criteria = %s" % (job, criteria))

            # Flush old jobs
            Job.age_jobs()

        return job

    @classmethod
    def _compute_handle(cls, table, criteria):
        h = hashlib.md5()
        h.update(str(table.id))

        if table.cacheable and not criteria.ignore_cache:
            # XXXCJ - Drop ephemeral columns when computing the cache handle,
            # since the list of columns is modifed at run time.   Typical use
            # case is an analysis table which creates a time-series graph of
            # the top 10 hosts -- one column per host.  The host columns will
            # change based on the run of the dependent table.
            #
            # Including epheremal columns causes some problems because the
            # handle is computed before the query is actually run, so it never
            # matches.
            #
            # May want to dig in to this further and make sure this doesn't
            # pick up cache files when we don't want it to
            h.update('.'.join([c.name for c in
                               table.get_columns(ephemeral=False)]))

            if table.criteria_handle_func:
                criteria = table.criteria_handle_func.function(criteria)

            for k, v in criteria.iteritems():
                #logger.debug("Updating hash from %s -> %s" % (k,v))
                h.update('%s:%s' % (k, v))
        else:
            # Table is not cacheable, instead use current time plus a random
            # value just to get a unique hash
            h.update(str(datetime.datetime.now()))
            h.update(str(random.randint(0, 10000000)))

        return h.hexdigest()

    def reference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount')+1)
        #logger.debug("%s: reference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def dereference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount')-1)
        #logger.debug("%s: dereference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def json(self, data=None):
        """ Return a JSON represention of this Job. """
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
            self.mark_progress(0)

            logger.debug("%s: Worker to run report" % str(self))
            # Lookup the query class for this table
            i = importlib.import_module(self.table.module)
            queryclass = i.TableQuery

            # Create an worker to do the work
            worker = Worker(self, queryclass)
            worker.start()

    def mark_error(self, message):
        logger.warning("%s failed: %s" % (self, message))
        self.safe_update(status=Job.ERROR,
                         progress=100,
                         message=message)

    def mark_complete(self):
        logger.info("%s complete" % self)
        self.safe_update(status=Job.COMPLETE,
                         progress=100,
                         message='')

    def mark_progress(self, progress, remaining=None):
        logger.debug("%s progress %s" % (self, progress))
        self.safe_update(status=Job.RUNNING,
                         progress=progress,
                         remaining=remaining)

    def datafile(self):
        """ Return the data file for this job. """
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)

    def data(self):
        """ Returns a pandas.DataFrame of data, or None if not available. """

        with transaction.commit_on_success():
            self.refresh()
            if not self.status == Job.COMPLETE:
                raise ValueError("Job not complete, no data available")

            self.reference("data()")

            e = None
            try:
                logger.debug("%s looking for data file: %s" %
                             (str(self), self.datafile()))
                if os.path.exists(self.datafile()):
                    df = pandas.load(self.datafile())
                    logger.debug("%s data loaded %d rows from file: %s" %
                                 (str(self), len(df), self.datafile()))
                else:
                    logger.debug("%s no data, missing data file: %s" %
                                 (str(self), self.datafile()))
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

            # Straggling numpy data types may cause problems
            # downstream (json encoding, for example), so strip
            # things down to just native ints and floats
            cleaned = []
            for row in vals:
                cleaned_row = []
                for v in row:
                    if isinstance(v, numpy.number):
                        v = numpy.asscalar(v)
                    cleaned_row.append(v)
                cleaned.append(cleaned_row)

            return cleaned
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
            old = datetime.timedelta(
                seconds=settings.APPS_DATASOURCE['job_age_old_seconds']
            )
        elif type(old) in [int, float]:
            old = datetime.timedelta(seconds=old)

        if ancient is None:
            ancient = datetime.timedelta(
                seconds=settings.APPS_DATASOURCE['job_age_ancient_seconds']
            )
        elif type(ancient) in [int, float]:
            ancient = datetime.timedelta(seconds=ancient)

        # Ancient jobs are deleted regardless of refcount
        now = datetime.datetime.now(tz=pytz.utc)
        try:
            (Job.objects.filter(touched__lte=now - ancient)).delete()
        except:
            logger.exception("Failed to delete ancient jobs")

        # Old jobs are deleted only if they have a refcount of 0
        try:
            (Job.objects.filter(touched__lte=now - old, refcount=0)).delete()
        except:
            logger.exception("Failed to delete old jobs")

        age_jobs_last_run = time.time()

    @classmethod
    def flush_incomplete(cls):
        jobs = Job.objects.filter(progress__lt=100)
        logger.info("Flushing %d incomplete jobs: %s" %
                    (len(jobs), [j.id for j in jobs]))
        jobs.delete()

    def done(self):
        self.refresh()
        logger.debug("%s status: %s - %s%%" % (str(self),
                                               self.status,
                                               self.progress))
        return self.status == Job.COMPLETE or self.status == Job.ERROR


@receiver(pre_delete, sender=Job)
def _my_job_delete(sender, instance, **kwargs):
    if instance.parent is not None:
        instance.parent.dereference(str(instance))
    if instance.datafile() and os.path.exists(instance.datafile()):
        try:
            os.unlink(instance.datafile())
        except OSError:
            # permissions issues, perhaps
            logger.error('OSError occurred when attempting to delete '
                         'job datafile: %s' % instance.datafile())


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

    def __repr__(self):
        return unicode(self)

    def run(self):
        self.do_run()
        sys.exit(0)


class SyncWorker(object):
    def __init__(self, job, queryclass):
        self.job = job
        self.queryclass = queryclass

    def __unicode__(self):
        return "<SyncWorker %s>" % (self.job)

    def __str__(self):
        return "<SyncWorker %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def start(self):
        self.do_run()

if settings.APPS_DATASOURCE['threading'] and not settings.TESTING:
    base_worker_class = AsyncWorker
else:
    base_worker_class = SyncWorker


class Worker(base_worker_class):

    def __init__(self, job, queryclass):
        super(Worker, self).__init__(job, queryclass)

    def do_run(self):
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
                        if col.datatype == 'time':
                            # The column is supposed to be time,
                            # make sure all values are datetime objects
                            if str(s.dtype).startswith(str(pandas.np.dtype('datetime64'))):
                                # Already a datetime
                                pass
                            elif str(s.dtype).startswith('int'):
                                # This is a numeric epoch, convert to datetime
                                s = s.values.astype('datetime64[s]')
                            elif str(s.dtype).startswith('float'):
                                # This is a numeric epoch as a float, possibly
                                # has subsecond resolution, convert to
                                # datetime but preserve up to millisecond
                                s = (1000 * s).values.astype('datetime64[ms]')
                            else:
                                # Possibly datetime object or a datetime string,
                                # hopefully astype() can figure it out
                                s = s.values.astype('datetime64[ms]')

                            df[col.name] = pandas.Series(s)

                        elif (col.isnumeric and
                              s.dtype == pandas.np.dtype('object')):
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
                      (isinstance(query.data, list) and len(query.data) == 0)):
                    df = None
                elif isinstance(query.data, pandas.DataFrame):
                    df = query.data
                else:
                    raise ValueError("Unrecognized query result type: %s" %
                                     type(query.data))

                if df is not None:
                    df = job.table.compute_synthetic(job, df)

                if df is not None:
                    df.save(job.datafile())
                    logger.debug("%s data saved to file: %s" % (str(self),
                                                                job.datafile()))
                else:
                    logger.debug("%s no data saved, data is empty" %
                                 (str(self)))

                logger.info("%s finished as COMPLETE" % self)
                job.refresh()
                if job.actual_criteria is None:
                    job.safe_update(actual_criteria=job.criteria)

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
                logger.error("%s finished with an error: %s" % (self,
                                                                job.message))

        except:
            logger.exception("%s raised an exception" % self)
            job.safe_update(
                status=job.ERROR,
                progress=100,
                message=traceback.format_exception_only(sys.exc_info()[0],
                                                        sys.exc_info()[1])
            )

        finally:
            job.dereference("Worker exiting")


class BatchJobRunner(object):

    def __init__(self, basejob, batchsize=4, min_progress=0, max_progress=100):
        self.basejob = basejob
        self.jobs = []
        self.batchsize = batchsize
        self.min_progress = min_progress
        self.max_progress = max_progress

    def __str__(self):
        return "BatchJobRunner (%s)" % self.basejob

    def add_job(self, job):
        self.jobs.append(job)


    def run(self):
        class JobList:
            def __init__(self, jobs):
                self.jobs = jobs
                self.index = 0
                self.count = len(jobs)

            def __nonzero__(self):
                return self.index < self.count

            def next(self):
                if self.index < self.count:
                    job = self.jobs[self.index]
                    self.index = self.index + 1
                    return job
                return None

        joblist = JobList(self.jobs)
        done_count = 0
        batch = []

        logger.info("%s: %d total jobs" % (self, joblist.count))

        while joblist and len(batch) < self.batchsize:
            job = joblist.next()
            batch.append(job)
            job.start()
            logger.debug("%s: starting batch job #%d (%s)"
                         % (self, joblist.index, job))

        # iterate until both jobs and batch are empty
        while joblist or batch:
            # check jobs in the batch
            rebuild_batch = False
            batch_progress = 0.0
            something_done = False
            for i,job in enumerate(batch):
                job.refresh()
                if job.done():
                    something_done = True
                    done_count = done_count + 1
                    if joblist:
                        batch[i] = joblist.next()
                        batch[i].start()
                        logger.debug("%s: starting batch job #%d (%s)"
                                     % (self, joblist.index, batch[i]))
                    else:
                        batch[i] = None
                        rebuild_batch = True
                else:
                    batch_progress = batch_progress + float(job.progress)

            total_progress = (float(done_count * 100) + batch_progress) / joblist.count
            job_progress = (float(self.min_progress) +
                            ((total_progress / 100.0) *
                             (self.max_progress - self.min_progress)))
            logger.debug("%s: progress %d%% (basejob %d%%) (%d/%d done, %d in batch)" %
                         (self, int(total_progress), int(job_progress),
                          done_count, joblist.count, len(batch)))
            self.basejob.mark_progress(job_progress)

            if not something_done:
                time.sleep(0.2)

            elif rebuild_batch:
                batch = [j for j in batch if j is not None]


        return

        for i in range(0, len(jobs), self.batchsize):
            batch = jobs[i:i+self.batchsize]
            batch_status = {}
            for j,job in enumerate(batch):
                batch_status[job.id] = False
                logger.debug("%s: starting job #%d (%s)"
                             % (self, j+i, job))
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
                            batch_progress += (float(job.progress) /
                                               float(self.batchsize))
                    else:
                        batch_progress += (100.0 / float(self.batchsize))

                total_progress = (i * 100.0 + batch_progress * self.batchsize) / len(jobs)
                job_progress = (self.min_progress +
                                (total_progress * (self.max_progress -
                                                   self.min_progress)) / 100)
                logger.debug("%s: batch[%d:%d] %d%% / total %d%% / job %d%%",
                             self, i, i+self.batchsize, int(batch_progress),
                             int(total_progress), int(job_progress))
                self.basejob.mark_progress(job_progress)
                if not batch_done:
                    time.sleep(interval)
                    #interval = (interval * 2) if interval < max_interval else max_interval
