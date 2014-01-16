# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os
import json
import logging
from cStringIO import StringIO

from django.db import models
from django.core import management

from project.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)


def create_device_fixture(strip_passwords=True):
    """ Dump devices to JSON file, optionally stripping passwords.
    """
    buf = StringIO()
    management.call_command('dumpdata', 'devices', stdout=buf)
    buf.seek(0)
    devices = list()
    for d in json.load(buf):
        if strip_passwords:
            del d['fields']['password']
        devices.append(d)

    fname = os.path.join(PROJECT_ROOT, 'initial_data', 'initial_devices.json')
    with open(fname, 'w') as f:
        f.write(json.dumps(devices, indent=2))

    logger.debug('Wrote %d devices to fixture file %s' % (len(devices), fname))


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

    def save(self, *args, **kwargs):
        super(Device, self).save(*args, **kwargs)
        create_device_fixture()
