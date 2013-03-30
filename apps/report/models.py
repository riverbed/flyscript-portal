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

from django.db import models
from django.http import HttpResponse

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

    def __unicode__(self):
        return self.title

class Widget(models.Model):
    tables = models.ManyToManyField(Table)
    report = models.ForeignKey(Report)
    title = models.CharField(max_length=100)
    row = models.IntegerField()
    col = models.IntegerField()
    colwidth = models.IntegerField(default=1)
    rows = models.IntegerField(default=-1)
    options = JSONField()

    module = models.CharField(max_length=100)
    uiwidget = models.CharField(max_length=100)
    uioptions = JSONField()
    
    objects = InheritanceManager()
    
    def __unicode__(self):
        return self.title

    def widgettype(self):
        return 'rvbd_%s.%s' % (self.module, self.uiwidget)

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
    
    def poll(self, ts):
        job = self.table().poll(ts)

        if not job.done():
            # job not yet done, return an empty data structure
            logger.debug("widget.poll: Not done yet, %d%% complete" % job.progress)
            resp = job.json()
        elif job.status == Job.ERROR:
            resp = job.json()
        else:
            import apps.report.modules
            widget_func = apps.report.modules.__dict__[self.module].__dict__[self.uiwidget]
            if self.rows > 0:
                tabledata = job.data()[:self.rows]
            else:
                tabledata = job.data()

            try:
                data = widget_func(self, tabledata)
                resp = job.json(data)
                logger.debug("widget.poll: Job complete")
            except:
                resp = job.json()
                resp['status'] = Job.ERROR
                resp['message'] = str(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
                traceback.print_exc()

            job.delete()
            
        resp['message'] = cgi.escape(resp['message'])
        return HttpResponse(json.dumps(resp))


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

