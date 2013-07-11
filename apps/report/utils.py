# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import os
import glob
import zipfile
import datetime
import subprocess

import pytz
from django.contrib.auth.models import User

from rvbd.common.timeutils import datetime_to_seconds

from project import settings

import logging
logger = logging.getLogger(__name__)


def debug_fileinfo(fname):
    st = os.stat(fname)
    logging.debug('%15s: mtime - %s, ctime - %s' % (os.path.basename(fname),
                                                    datetime.datetime.fromtimestamp(st.st_mtime),
                                                    datetime.datetime.fromtimestamp(st.st_ctime)))


def create_debug_zipfile(no_summary=False):
    """ Collects logfiles and system info into a zipfile for download/email

        `no_summary` indicates whether to include system information from
                     the helper script `flyscript_about.py` as part of the
                     zipped package.  Default is to include the file.
    """
    # setup correct timezone based on admin settings
    admin = User.objects.filter(is_superuser=True)[0]
    tz = pytz.timezone(admin.userprofile.timezone)
    current_tz = os.environ['TZ']

    try:
        # save TZ to environment for zip to use
        os.environ['TZ'] = str(tz)

        # if zlib is available, then let's compress the files
        # otherwise we will just append them like a tarball
        try:
            import zlib
            compression = zipfile.ZIP_DEFLATED
        except ImportError:
            compression = zipfile.ZIP_STORED

        # setup the name, correct timezone, and open the zipfile
        now = datetime_to_seconds(datetime.datetime.now(tz))
        archive_name = os.path.join(settings.PROJECT_ROOT, 'debug-%d.zip' % now)

        myzip = zipfile.ZipFile(archive_name, 'w', compression=compression)

        try:
            # find all of the usual logfiles
            filelist = glob.glob(os.path.join(settings.PROJECT_ROOT, 'log*'))

            logging.debug('zipping log files ...')
            for fname in filelist:
                debug_fileinfo(fname)
                myzip.write(fname)

            if not no_summary:
                logging.debug('running about script')
                p = subprocess.Popen('flyscript_about.py', stdout=subprocess.PIPE, 
                                                           stderr=subprocess.PIPE)
                response = '\n'.join([p.stdout.read(), p.stderr.read()])
                logging.debug('zipping about script')
                myzip.writestr('system_summary.txt', response)
                p.stdout.close()
                p.stderr.close()
        finally:
            myzip.close()

    finally:
        # return env to its prior state
        os.environ['TZ'] = current_tz

    return archive_name



