#
# This file includes example settings and configuration to enable
# LDAP authentication for the Portal.
#
# Two additional packages are required to implement this feature:
#    ldap
#    django-auth-ldap
#
# After those packages have been installed into the python environment,
# copy the lines over to the settings_local.py file and they will be
# picked up upon server restart.
#

# LDAP Authentication setup
import ldap
from django_auth_ldap.config import LDAPSearch

AUTHENTICATION_BACKENDS = (
    # Uncomment the following and settings below to enable LDAP Auth
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)

#
# Configure the LDAP Authentication Server
#

# The LDAP server to authenticate with, for example:
#   ldap://localhost:389
AUTH_LDAP_SERVER_URI = 'ldap://ldap.example.com'

# Any additional connection options
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}

# LDAP Search Base for queries, replace with valid parameters
search_base = "cn=users,dc=example,dc=com"

# Uncomment one of the following groups of options
# See here for more information:
#    http://pythonhosted.org/django-auth-ldap/authentication.html

## Direct Bind Authentication
#AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = True
#AUTH_LDAP_USER_DN_TEMPLATE = 'example_domain\%(user)s'
#AUTH_LDAP_USER_SEARCH = LDAPSearch(search_base,
#                                   ldap.SCOPE_SUBTREE,
#                                   "(mailNickname=%(user)s)")

## Anonymous Search/Bind
#AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = False
#AUTH_LDAP_USER_DN_TEMPLATE = '%(user)s'
#AUTH_LDAP_BIND_DN = ""
#AUTH_LDAP_BIND_PASSWORD = ""
#AUTH_LDAP_USER_SEARCH = LDAPSearch(search_base,
#                                   ldap.SCOPE_SUBTREE,
#                                   "(uid=%(user)s)")

## Fixed Account Search/Bind
#AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = False
#AUTH_LDAP_USER_DN_TEMPLATE = '%(user)s'
#AUTH_LDAP_BIND_DN = "<username>"
#AUTH_LDAP_BIND_PASSWORD = "<password>"
#AUTH_LDAP_USER_SEARCH = LDAPSearch(search_base,
#                                   ldap.SCOPE_SUBTREE,
#                                   "(uid=%(user)s)")
