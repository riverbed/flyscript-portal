# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import sys
import pkg_resources

from rvbd_common.apps.plugins import register


def load_plugins():
    """ Loads and registers externally installed Portal plugins. """

    ## example entry points for setup.py file:
    # entry_points={
    #    'portal.plugins': [
    #         'portal_fancy_report = portal_fancy_report.plugins:FancyReportPlugin'
    #     ],
    # },

    for ep in pkg_resources.iter_entry_points('portal.plugins'):
        try:
            plugin = ep.load()
        except Exception:
            import traceback
            msg = "Failed to load plugin %r:\n%s" % (ep.name,
                                                     traceback.format_exc())
            print >> sys.stderr, msg
        else:
            register(plugin)
