# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import logging

from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User

import pytz

logger = logging.getLogger(__name__)


#######################################################################
#
# User Preferences
#
TIMEZONE_CHOICES = zip(pytz.common_timezones, pytz.common_timezones)

MAPS_VERSIONS = ('DISABLED', 'DEVELOPER', 'FREE', 'BUSINESS')
MAPS_VERSION_CHOICES = zip(MAPS_VERSIONS, map(str.title, MAPS_VERSIONS))


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    timezone = models.CharField(max_length=50, 
                                default='UTC',
                                choices=TIMEZONE_CHOICES)
    ignore_cache = models.BooleanField(default=False,
                                       help_text='Force all reports to bypass cache')
    developer = models.BooleanField(default=False, 
                                    verbose_name='developer mode')
    maps_version = models.CharField(default='DISABLED',
                                    max_length=30,
                                    verbose_name='Maps Version',
                                    choices=MAPS_VERSION_CHOICES)
    maps_api_key = models.CharField(max_length=100, 
                                    verbose_name='Maps API Key',
                                    blank=True, 
                                    null=True)

    # hidden fields
    timezone_changed = models.BooleanField(default=False)
    profile_seen = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.timezone != 'UTC':
            self.timezone_changed = True
        super(UserProfile, self).save(*args, **kwargs)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)

