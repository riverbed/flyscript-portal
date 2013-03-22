# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import sys

from django.db import models

from apps.datasource.models import Device
from apps.datasource.devicemanager import DeviceManager



class Utility(models.Model):
    """ Base class for tools and scripts installed locally
    """
    name = models.CharField(max_length=200)
    path = models.CharField(max_length=200)


class Parameter(models.Model):
    """ Key/Value pairs for inputs to Utilities

    Terminology:

        Option                  Name        Flag    Value
        -t                      -t          Yes     None
        --force-ssl             --force-ssl Yes     None
        -u USERNAME             -u          No      USERNAME
        --username=USERNAME     --username  No      USERNAME
        --password=PASSWORD     NOT SUPPORTED
        <argument>              <argument>  No      None

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
    default = models.CharField(max_length=200, blank=True)


class Results(models.Model):
    """ Storage of Utility results
    """
    utility = models.ForeignKey(Utility)
    run_date = models.DateTimeField(auto_now=True)
    results = models.TextField(editable=False)


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
