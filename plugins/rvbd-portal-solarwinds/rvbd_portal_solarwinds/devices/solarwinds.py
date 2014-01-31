# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import json
import base64
import logging

from rvbd.common.connection import Connection
from rvbd.common.service import Service

logger = logging.getLogger(__name__)


def new_device_instance(*args, **kwargs):
    # Used by DeviceManager to create a Profiler instance
    return Solarwinds(*args, **kwargs)


class Solarwinds(Service):
    """ Solarwinds device instance. """
    def __init__(self, host, port, auth):
        self.auth = auth
        super(Solarwinds, self).__init__('solarwinds', host, port, auth)

        self.base_url = ("https://%s:%s/SolarWinds/InformationService/v3/Json/"
                         % (host, port))

    def check_api_versions(self, api_versions):
        pass

    def authenticate(self, auth):
        # Use HTTP Basic authentication only
        s = base64.b64encode("%s:%s" % (self.auth.username, self.auth.password))
        self.conn.add_headers({'Authorization': 'Basic %s' % s})

        logger.info("Authenticated using BASIC")

    # methods from Solarwinds example, SwisClient.py
    def query(self, query, **params):
        return self._req("POST", "Query",
                         {'query': query, 'parameters': params})

    def invoke(self, entity, verb, *args):
        return self._req("POST", "Invoke/%s/%s" % (entity, verb), args)

    def create(self, entity, **properties):
        return self._req("POST", "Create/" + entity, properties)

    def read(self, uri):
        return self._req("GET", uri)

    def update(self, uri, **properties):
        self._req("POST", uri, properties)

    def delete(self, uri):
        self._req("DELETE", uri)

    def _req(self, method, frag, data=None):
        return self.conn.json_request(method,
                                      self.base_url + frag,
                                      body=json.dumps(data))
