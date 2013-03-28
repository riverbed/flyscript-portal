# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import sys
import datetime

from django.db import models

from apps.datasource.models import Device
from apps.datasource.devicemanager import DeviceManager

import logging
logger = logging.getLogger(__name__)

class Utility(models.Model):
    """ Base class for tools and scripts installed locally
    """
    name = models.CharField(max_length=200)
    path = models.CharField(max_length=200)
    islogfile = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s %s %s' % (self.name, self.path, self.islogfile)


class ParameterManager(models.Manager):
    def get_param_string(self, utility):
        params = Parameter.objects.filter(utility=utility)
        return ' '.join(p.construct() for p in params)


class Parameter(models.Model):
    """ Key/Value pairs for inputs to Utilities

    Terminology:

        Option                  Name        Flag    Value
        -t                      -t          Yes     None
        --force-ssl             --force-ssl Yes     None
        -u USERNAME             -u          No      USERNAME
        --username=USERNAME     --username  No      USERNAME
        --password=PASSWORD     NOT SUPPORTED
        <argument>              <argument>  Yes      None

    So arguments are handled the same as Flag options, though
    ordering is important.

    Authentication should be handled via OAUTH tokens, which
    can be stored using one of the mechanisms above.
    """
    utility = models.ForeignKey(Utility)
    index = models.IntegerField()
    name = models.CharField(max_length=100)
    flag = models.BooleanField(default=False)
    value = models.CharField(max_length=100, blank=True)

    objects = ParameterManager()

    def construct(self):
        """ Return string representation
        """
        # XXX add some better processing to this
        if self.flag:
            return self.name
        elif self.name.startswith('-'):
            token = ' '
            if self.name.startswith('--'):
                token = '='

            if self.value:
                return '%s%s%s' % (self.name, token, self.value)
        else:
            return self.name


class ResultsManager(models.Manager):
    def clean_results(self, days=30, number=30):
        """ Remove Results objects older than `days` or when
            there is more than `number` of objects
        """
        old_date = datetime.datetime.now() - datetime.timedelta(days=days)
        results = Results.objects.filter(run_date__lte=old_date)
        logger.debug('Found %d old results to delete.' % len(results))
        results.delete()

        results = Results.objects.all().order_by('run_date')
        if len(results) > number:
            offset = len(results) - number
            to_delete = results[:offset]
            logging.debug('Considering the following %d Results for deletion:' % offset)
            logging.debug(to_delete)


class Results(models.Model):
    """ Storage of Utility results
    """
    utility = models.ForeignKey(Utility)
    run_date = models.DateTimeField(auto_now=True)
    results = models.TextField(editable=False)

    objects = ResultsManager()

    def __unicode__(self):
        return '%s %s' % (self.utility, self.run_date)


class Job(models.Model):
    """ Running Utility information
    """
    handle = models.CharField(max_length=100)

    NEW = 0
    RUNNING = 1
    COMPLETE = 2
    ERROR = 3

    status = models.IntegerField(default=NEW,
                                 choices=((NEW, "New"),
                                          (RUNNING, "Running"),
                                          (COMPLETE, "Complete"),
                                          (ERROR, "Error")))

    message = models.CharField(max_length=200, default="")
    progress = models.IntegerField(default=-1)
    remaining = models.IntegerField(default=-1)

    def __unicode__(self):
        return "%s, %s %s%%" % (self.handle, self.status, self.progress)

    def done(self):
        return self.status == Job.COMPLETE or self.status == Job.ERROR
