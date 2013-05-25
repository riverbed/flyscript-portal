# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import sys
import cgi
import json
import logging
import traceback
import importlib

from django.db import models
from django.http import HttpResponse
from django.db.models import Max, Sum

from model_utils.managers import InheritanceManager
from jsonfield import JSONField
from apps.datasource.models import Table, Job
from libs.options import Options

logger = logging.getLogger(__name__)


class WidgetOptions(Options):
    def __init__(self, key=None, value=None, axes=None, *args, **kwargs):
        super(Options, self).__init__(*args, **kwargs)
        self.key = key
        self.value = value
        if axes:
            self.axes = Axes(axes)


#######################################################################
#
# Reports and Widgets
#

class Report(models.Model):
    title = models.CharField(max_length=200)
    position = models.IntegerField(default=0)

    def __unicode__(self):
        return self.title

class Widget(models.Model):
    tables = models.ManyToManyField(Table)
    report = models.ForeignKey(Report)
    title = models.CharField(max_length=100)
    row = models.IntegerField()
    col = models.IntegerField()
    width = models.IntegerField(default=1)
    height = models.IntegerField(default=300)
    rows = models.IntegerField(default=-1)
    options = JSONField()

    module = models.CharField(max_length=100)
    uiwidget = models.CharField(max_length=100)
    uioptions = JSONField()
    
    objects = InheritanceManager()
    
    def __unicode__(self):
        return self.title

    def widgettype(self):
        return 'rvbd_%s.%s' % (self.module.split('.')[-1], self.uiwidget)

    def get_uioptions(self):
        return json.dumps(self.uioptions)

    def get_options(self):
        return WidgetOptions.decode(json.dumps(self.options))

    def get_option(self, option, default=None):
        try:
            return self.options[option]
        except KeyError:
            return default

    def table(self, i=0):
        return self.tables.all()[i]

    def compute_row_col(self):
        rowmax = Widget.objects.filter(report=self.report).aggregate(Max('row'))
        row = rowmax['row__max']
        if row is None:
            row = 1
            col = 1
        else:
            widthsum = Widget.objects.filter(report=self.report, row=row).aggregate(Sum('width'))
            width = widthsum['width__sum']
            if width + self.width > 12:
                row = row + 1
                col = 1
            else:
                col = width + 1
        self.row = row
        self.col = col

class WidgetJob(models.Model):

    widget = models.ForeignKey(Widget)
    job = models.ForeignKey(Job)

    def __unicode__(self):
        return "%s: widget %s, job %s" % (self.id, self.widget.id, self.job.id)
    
    def response(self):
        job = self.job
        widget = self.widget
        if not job.done():
            # job not yet done, return an empty data structure
            logger.debug("WidgetJob %s: Not done yet, %d%% complete" % (str(self), job.progress))
            resp = job.json()
        elif job.status == Job.ERROR:
            resp = job.json()
            self.delete()
        else:
            try:
                i = importlib.import_module(widget.module)
                widget_func = i.__dict__[widget.uiwidget].process
                if widget.rows > 0:
                    tabledata = job.data()[:widget.rows]
                else:
                    tabledata = job.data()
                    
                if tabledata is None or len(tabledata) == 0:
                    resp = job.json()
                    resp['status'] = Job.ERROR
                    resp['message'] = "No data returned"
                else:
                    data = widget_func(widget, tabledata)
                    resp = job.json(data)
                    logger.debug("WidgetJob %s complete" % str(self))
            except:
                resp = job.json()
                resp['status'] = Job.ERROR
                ei = sys.exc_info()
                resp['message'] = str(traceback.format_exception_only(ei[0], ei[1]))
                traceback.print_exc()
            
            # XXXCJ - should delete the job?  
            #job.delete()
            self.delete()
            
        resp['message'] = cgi.escape(resp['message'])
        try:
            return HttpResponse(json.dumps(resp))
        except TypeError:
            from IPython import embed; embed()
    
class Axes:
    def __init__(self, definition):
        self.definition = definition

    def getaxis(self, colname):
        if self.definition is not None:
            for n,v in self.definition.items():
                if ('columns' in v) and (colname in v['columns']):
                    return int(n)
        return 0

    def position(self, axis):
        axis = str(axis)
        if ((self.definition is not None) and 
            (axis in self.definition) and ('position' in self.definition[axis])):
            return self.definition[axis]['position']
        return 'left'

