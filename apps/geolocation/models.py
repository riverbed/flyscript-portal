# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.db import models
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.exceptions import ObjectDoesNotExist

import logging
logger = logging.getLogger('geolocation')

from apps.datasource.models import *

#######################################################################
#
# Locations
#

class Location(models.Model):
    name = models.CharField(max_length=200)
    address = models.IPAddressField()
    mask = models.IPAddressField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    def __unicode__(self):
        return self.name

