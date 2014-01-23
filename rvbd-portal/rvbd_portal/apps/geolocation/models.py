# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from django.db import models

import logging
logger = logging.getLogger(__name__)

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
