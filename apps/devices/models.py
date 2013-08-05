# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging

from django.db import models

logger = logging.getLogger(__name__)


class Device(models.Model):
    """ Records for devices referenced in report configuration pages.

        Actual instantiations of Device objects handled through DeviceManager
        class in devicemanager.py module.
    """
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)
    host = models.CharField(max_length=200)
    port = models.IntegerField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    # only enabled devices will require field validation
    enabled = models.BooleanField(default=True)

    def __unicode__(self):
        return '%s (%s:%s)' % (self.name, self.host, self.port)