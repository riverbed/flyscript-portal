# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import inspect
import logging

from rvbd.common.jsondict import JsonDict

from django.db import models
from django.db.models import Max, Sum
from django.template.defaultfilters import slugify

from model_utils.managers import InheritanceManager
from apps.datasource.models import Table, Job, TableCriteria

from libs.fields import PickledObjectField

logger = logging.getLogger(__name__)


class WidgetOptions(JsonDict):
    _default = {'key': None,
                'value': None,
                'axes': None}


def get_caller_name(match='config.'):
    """ Determine filename of calling function.
        Used to determine source of Report class definition.
    """
    frame = inspect.stack()[1]
    frm = frame[0]
    mod = inspect.getmodule(frm)
    while frm:
        if mod and mod.__name__.startswith(match):
            return mod.__name__
        else:
            old_frm, frm = frm, frm.f_back
            mod = inspect.getmodule(frm)
            del old_frm         # avoid reference cycles and leaks
    del frm
    return ''


class Report(models.Model):
    """ Defines the collection of Widgets and criteria for a Report view
    """
    title = models.CharField(max_length=200)
    position = models.IntegerField(default=0)
    criteria = models.ManyToManyField(TableCriteria, null=True)
    sourcefile = models.CharField(max_length=200, default=get_caller_name)
    slug = models.SlugField()

    def save(self, *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.sourcefile.split('.')[-1])
        super(Report, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title


class Widget(models.Model):
    """ Defines a UI widget and the source datatables
    """
    tables = models.ManyToManyField(Table)
    report = models.ForeignKey(Report)
    title = models.CharField(max_length=100)
    row = models.IntegerField()
    col = models.IntegerField()
    width = models.IntegerField(default=1)
    height = models.IntegerField(default=300)
    rows = models.IntegerField(default=-1)
    options = PickledObjectField()

    module = models.CharField(max_length=100)
    uiwidget = models.CharField(max_length=100)
    uioptions = PickledObjectField()
    
    objects = InheritanceManager()
    
    def __unicode__(self):
        return self.title

    def widgettype(self):
        return 'rvbd_%s.%s' % (self.module.split('.')[-1], self.uiwidget)

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
    """ Query point for status of Jobs for each Widget.
    """
    widget = models.ForeignKey(Widget)
    job = models.ForeignKey(Job)

    def __unicode__(self):
        return "<WidgetJob %s: widget %s, job %s>" % (self.id, 
                                                      self.widget.id,
                                                      self.job.id)
    

class Axes:
    def __init__(self, definition):
        self.definition = definition

    def getaxis(self, colname):
        if self.definition is not None:
            for n, v in self.definition.items():
                if ('columns' in v) and (colname in v['columns']):
                    return int(n)
        return 0

    def position(self, axis):
        axis = str(axis)
        if ((self.definition is not None) and 
            (axis in self.definition) and ('position' in self.definition[axis])):
            return self.definition[axis]['position']
        return 'left'

