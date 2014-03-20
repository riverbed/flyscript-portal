# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import socket
import httplib
import urllib2
import logging
import urlparse
from urllib import addinfourl

from ntlm import ntlm
from ntlm.HTTPNtlmAuthHandler import HTTPNtlmAuthHandler
from sharepoint import SharePointSite, basic_auth_opener


logger = logging.getLogger(__name__)


class PatchedHTTPNtlmAuthHandler(HTTPNtlmAuthHandler):
    """ Handle recent NTLM changes until package updated. """
    # XXX: patch based on version 1.0.1 of python-ntlm
    # see https://code.google.com/p/python-ntlm/issues/detail?id=17
    # this class applies patch from comment #3
    def retry_using_http_NTLM_auth(self, req, auth_header_field, realm, headers):
        user, pw = self.passwd.find_user_password(realm, req.get_full_url())
        if pw is not None:
            # ntlm secures a socket, so we must use the same socket for the complete handshake
            headers = dict(req.headers)
            headers.update(req.unredirected_hdrs)
            auth = 'NTLM %s' % ntlm.create_NTLM_NEGOTIATE_MESSAGE(user)
            if req.headers.get(self.auth_header, None) == auth:
                return None
            headers[self.auth_header] = auth

            host = req.get_host()
            if not host:
                raise urllib2.URLError('no host given')
            h = None
            if req.get_full_url().startswith('https://'):
                h = httplib.HTTPSConnection(host) # will parse host:port
            else:
                h = httplib.HTTPConnection(host) # will parse host:port
            h.set_debuglevel(self._debuglevel)
            # we must keep the connection because NTLM authenticates the connection, not single requests
            headers["Connection"] = "Keep-Alive"
            headers = dict((name.title(), val) for name, val in headers.items())
            h.request(req.get_method(), req.get_selector(), req.data, headers)
            r = h.getresponse()
            r.begin()
            r._safe_read(int(r.getheader('content-length')))
            if r.getheader('set-cookie'):
                # this is important for some web applications that store authentication-related info in cookies (it took a long time to figure out)
                headers['Cookie'] = r.getheader('set-cookie')
            r.fp = None # remove the reference to the socket, so that it can not be closed by the response object (we want to keep the socket open)
            auth_header_value = r.getheader(auth_header_field, None)

            # begin patch
            if ',' in auth_header_value:
                auth_header_value, postfix = auth_header_value.split(',', 1)
            # end patch

            (ServerChallenge, NegotiateFlags) = ntlm.parse_NTLM_CHALLENGE_MESSAGE(auth_header_value[5:])
            user_parts = user.split('\\', 1)
            DomainName = user_parts[0].upper()
            UserName = user_parts[1]
            auth = 'NTLM %s' % ntlm.create_NTLM_AUTHENTICATE_MESSAGE(ServerChallenge, UserName, DomainName, pw, NegotiateFlags)
            headers[self.auth_header] = auth
            headers["Connection"] = "Close"
            headers = dict((name.title(), val) for name, val in headers.items())
            try:
                h.request(req.get_method(), req.get_selector(), req.data, headers)
                # none of the configured handlers are triggered, for example redirect-responses are not handled!
                response = h.getresponse()
                def notimplemented():
                    raise NotImplementedError
                response.readline = notimplemented
                infourl = addinfourl(response, response.msg, req.get_full_url())
                infourl.code = response.status
                infourl.msg = response.reason
                return infourl
            except socket.error, err:
                raise urllib2.URLError(err)
        else:
            return None


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
    """ Simple wrapper around sharepoint objects.

    Defaults to NTLM authentication, to use basic auth, call the method
    `set_basic_auth` or write a separate handler and overwrite the `opener`
    instance variable.
    """
    def __init__(self, host, username, password):
        self.host = host

        password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, host, username, password)
        auth_handler = PatchedHTTPNtlmAuthHandler(password_manager)
        self.opener = urllib2.build_opener(auth_handler)

    def set_basic_auth(self, username, password):
        self.opener = basic_auth_opener(self.host, username, password)

    def get_site_object(self, site_url):
        url = urlparse.urljoin(self.host, site_url)
        return SharePointSite(url, self.opener)
