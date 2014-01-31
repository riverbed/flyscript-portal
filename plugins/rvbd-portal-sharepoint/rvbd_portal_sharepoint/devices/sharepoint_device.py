# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging
import urlparse

from sharepoint import SharePointSite, basic_auth_opener


logger = logging.getLogger(__name__)


def new_device_instance(*args, **kwargs):
    # Used by DeviceManager to create a device instance

    # this logs into the sharepoint domain, passing an authorization
    # which is used for further access to particular sites
    if 'port' in kwargs and kwargs['port']:
        host = '%s:%s' % (kwargs['host'], kwargs['port'])
    else:
        host = kwargs['host']

    auth = kwargs['auth']
    return SharepointDevice(host, auth.username, auth.password)


class SharepointDevice(object):
    """ Simple wrapper around sharepoint objects """
    def __init__(self, host, username, password):
        self.host = host
        self.opener = basic_auth_opener(host, username, password)

    def get_site_object(self, site_url):
        url = urlparse.urljoin(self.host, site_url)
        return SharePointSite(url, self.opener)


