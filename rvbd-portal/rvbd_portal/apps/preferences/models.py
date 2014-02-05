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
from django.db.models.signals import post_save
from django.core import management
from django.contrib.auth.models import User
from django.conf import settings
import pytz


logger = logging.getLogger(__name__)


#######################################################################
#
# User Preferences
#
TIMEZONE_CHOICES = zip(pytz.common_timezones, pytz.common_timezones)

MAPS_VERSIONS = ('DISABLED',            # Google Maps Versions
                 'DEVELOPER',
                 'FREE',
                 'BUSINESS',
                 'OPEN_STREET_MAPS',    # Open Street Maps
                 #'STATIC_MAPS'          # Static library created maps
                 )
MAPS_VERSION_CHOICES = zip(MAPS_VERSIONS, map(str.title, MAPS_VERSIONS))


def create_preference_fixture(initial_admin_only=True):
    """Dump preferences to JSON file for safe keeping.

    Marks all preference objects as "not seen" so they will still
    appear after a reset to confirm choices.

    `initial_admin_only` set to True will only store preferences
    where the user id exists in the initial_admin_user file to
    avoid conflicts on database reloads.
    """
    buf = StringIO()
    management.call_command('dumpdata', 'preferences', stdout=buf)
    buf.seek(0)
    preferences = list()

    if initial_admin_only:
        admin_file = os.path.join(settings.PROJECT_ROOT,
                                  'initial_data',
                                  'initial_admin_user.json')
        with open(admin_file) as f:
            admin_ids = set(x['pk'] for x in json.load(f))

        for pref in json.load(buf):
            pref['fields']['profile_seen'] = False
            if pref['fields']['user'] in admin_ids:
                preferences.append(pref)

    else:
        for pref in json.load(buf):
            pref['fields']['profile_seen'] = False
            preferences.append(pref)

    fname = os.path.join(settings.PROJECT_ROOT,
                         'initial_data',
                         'initial_preferences.json')

    with open(fname, 'w') as f:
        f.write(json.dumps(preferences, indent=2))

    logger.debug('Wrote %d preferences to fixture file %s' % (len(preferences),
                                                              fname))


class UserProfile(models.Model):
    user = models.OneToOneField(User)
    timezone = models.CharField(max_length=50,
                                default='UTC',
                                choices=TIMEZONE_CHOICES)
    ignore_cache = models.BooleanField(default=False,
                                       help_text='Force all reports to '
                                                 'bypass cache')
    developer = models.BooleanField(default=False,
                                    verbose_name='developer mode')
    maps_version = models.CharField(max_length=30,
                                    verbose_name='Maps Version',
                                    choices=MAPS_VERSION_CHOICES,
                                    default='DISABLED')
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

        if self.profile_seen:
            # only save as a result of user save
            create_preference_fixture()


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
