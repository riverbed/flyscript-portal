# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import os
import sys
import glob
import zipfile
import platform
import pkg_resources
from datetime import datetime

import pytz
from django.contrib.auth.models import User

from rvbd.common.timeutils import datetime_to_seconds

from project import settings

import logging
logger = logging.getLogger(__name__)


def debug_fileinfo(fname):
    st = os.stat(fname)
    logging.debug('%15s: mtime - %s, ctime - %s' % (os.path.basename(fname),
                                                    datetime.fromtimestamp(st.st_mtime),
                                                    datetime.fromtimestamp(st.st_ctime)))


def system_info():
    """ Local version of the flyscript_about.py script
    """
    output = []
    try:
        dist = pkg_resources.get_distribution("flyscript")
        output.append("Package 'flyscript' version %s installed" % dist.version)
    except pkg_resources.DistributionNotFound:
        output.append("Package not found: 'flyscript'")
        output.append("Check the installation")
        
    import rvbd
    import pkgutil

    pkgpath = os.path.dirname(rvbd.__file__)

    output.append("")
    output.append("Path to source:\n  %s" % pkgpath)
    output.append("")
    output.append("Modules provided:")
    for (loader, name, ispkg) in pkgutil.walk_packages([pkgpath]):
        output.append("  rvbd.%s" % name)

    output.append("")
    output.append("Python information:")
    output.append('Version      : %s' % str(platform.python_version()))
    output.append('Version tuple: %s' % str(platform.python_version_tuple()))
    output.append('Compiler     : %s' % str(platform.python_compiler()))
    output.append('Build        : %s' % str(platform.python_build()))
    output.append('Architecture : %s' % str(platform.architecture()))

    output.append("")
    output.append("Platform information:")
    output.append(platform.platform())
    output.append('system   : %s' % str(platform.system()))
    output.append('node     : %s' % str(platform.node()))
    output.append('release  : %s' % str(platform.release()))
    output.append('version  : %s' % str(platform.version()))
    output.append('machine  : %s' % str(platform.machine()))
    output.append('processor: %s' % str(platform.processor()))

    output.append("")
    output.append("Python path:")
    output.append('\n'.join(sys.path))
    return output


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
        now = datetime_to_seconds(datetime.now(tz))
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
                response = '\n'.join(system_info())
                logging.debug('zipping about script')
                myzip.writestr('system_summary.txt', response)
        finally:
            myzip.close()

    finally:
        # return env to its prior state
        os.environ['TZ'] = current_tz

    return archive_name
