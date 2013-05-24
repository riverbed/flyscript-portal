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

class UserProfile(models.Model):
    user = models.OneToOneField(User)
    timezone = models.CharField(max_length=50, default='UTC', choices=TIMEZONE_CHOICES)
    timezone_changed = models.BooleanField(default=False)
    developer = models.BooleanField(default=False, verbose_name='developer mode')

    def save(self, *args, **kwargs):
        if self.timezone != 'UTC':
            self.timezone_changed = True
        super(UserProfile, self).save(*args, **kwargs)

def create_user_profile(sender, instance, created, **kwargs):
    #from IPython import embed; embed()
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)

