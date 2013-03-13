# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from time import sleep
import math
import datetime
import shutil
import os
import pickle
import sys
import traceback
import threading
import json
import cgi
from model_utils.managers import InheritanceManager
from libs.fields import PickledObjectField
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.exceptions import ObjectDoesNotExist
from libs.nicescale import NiceScale
from jsonfield import JSONField

import logging
logger = logging.getLogger('report')

from apps.datasource.models import *

#######################################################################
#
# Reports and Widgets
#

class Report(models.Model):
    title = models.CharField(max_length=200)

    def __unicode__(self):
        return self.title

class Widget(models.Model):
    report = models.ForeignKey(Report)
    datatable = models.ForeignKey(DataTable)
    title = models.CharField(max_length=100)
    row = models.IntegerField()
    col = models.IntegerField()
    colwidth = models.IntegerField(default=1)
    rows = models.IntegerField(default=-1)
    options = JSONField()

    uilib = models.CharField(max_length=100)
    uiwidget = models.CharField(max_length=100)
    uioptions = JSONField()
    
    objects = InheritanceManager()
    
    def __unicode__(self):
        return self.title

    def widgettype(self):
        return 'rvbd_%s.%s' % (self.uilib, self.uiwidget)

    def get_uioptions(self):
        return json.dumps(self.uioptions)

    def get_option(self, option, default=None):
        if option in self.options:
            return self.options[option]
        else:
            return default

    def poll(self, ts):
        job = self.datatable.poll(ts)

        if not job.done():
            # job not yet done, return an empty data structure
            logger.debug("widget.poll: Not done yet, %d%% complete" % job.progress)
            resp = job.json()
        elif job.status == Job.ERROR:
            resp = job.json()
        else:
            import apps.report.uilib
            widget_func = apps.report.uilib.__dict__[self.uilib].__dict__[self.uiwidget]
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

