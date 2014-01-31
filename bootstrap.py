#!/usr/bin/env python

import os
import sys
import subprocess

import pip


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(BASE_DIR, 'plugins')
SDIST_DIR = os.path.join(PLUGINS_DIR, 'sdist')

LOCAL_SETTINGS = os.path.join(BASE_DIR, 'project', 'settings_local.py')

LOCAL_SETTINGS_CONTENT = """
# LDAP Authentication setup
# To use LDAP, pip install the following two packages:
# python-ldap==2.4.13
# django-auth-ldap==1.1.7

# Now uncomment the next two import lines, and configure
# using AUTH_LDAP settings below
#import ldap
#from django_auth_ldap.config import LDAPSearch

AUTHENTICATION_BACKENDS = (
    # Uncomment the following and settings below to enable LDAP Auth
    #'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)

#
# Configure the LDAP Authentication Server
#

# The LDAP server to authenticate with, for example:
#   ldap://localhost:389
AUTH_LDAP_SERVER_URI = 'ldap://localhost:389'

# Any additional connection options
AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0
}

# LDAP Search Base for queries, replace with valid parameters
search_base = "ou=users,dc=example,dc=com"

# Uncomment one of the following groups of options
# See here for more information:
#    http://pythonhosted.org/django-auth-ldap/authentication.html

## Direct Bind Authentication
#AUTH_LDAP_BIND_AS_AUTHENTICATING_USER = True
#AUTH_LDAP_USER_DN_TEMPLATE = '%(user)s'
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
"""


def show_help():
    print "%s [install|uninstall|develop]" % sys.argv[0]
    print 
    print "Install or remove all of the included Portal plugins."


def which_pip():
    os.system('which pip')
    print __file__
    #from IPython import embed; embed()


def create_local_settings():
    """ Creates local settings file if none exists.
    """

    if not os.path.exists(LOCAL_SETTINGS):
        with open(LOCAL_SETTINGS, 'w') as f:
            f.write(LOCAL_SETTINGS_CONTENT)

        print '*****'
        print 'Local configuration file created: %s' % LOCAL_SETTINGS
        print '*****'


def create_sdists():
    if not os.path.isdir(SDIST_DIR):
        os.mkdir(SDIST_DIR)

    for pkg_name, root in find_plugins():
        os.chdir(root)
        os.system('python setup.py sdist --dist-dir %s' % SDIST_DIR)


def install_package(path, develop=False):
    """ pip install the package at `path`. """
    if develop:
        os.system('pip install --no-deps -e %s' % path)
    else:
        os.system('pip install --find-links %s %s' % (SDIST_DIR, path))


def uninstall_package(pkg_name):
    cmd = 'pip freeze'.split()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in p.stdout.readlines():
        if pkg_name in line:
            cmd = 'pip uninstall %s' % pkg_name
            p = subprocess.Popen(cmd.split(), 
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            p.stdin.write('y\n')
            print ''.join(p.stdout.readlines())
            break
    else:
        print 'Package %s not installed.' % pkg_name


def find_plugins():

    yield 'rvbd-portal', os.path.join(BASE_DIR, 'rvbd-portal')

    for root, dirs, files in os.walk(PLUGINS_DIR):
        #print root, dirs, files
        if 'setup.py' in files:
            dirs[:] = []
            pkg_name = os.path.basename(root)
            yield pkg_name, root


def install_plugins(develop=False):
    uninstall_plugins()
    for pkg_name, pkg_dir in find_plugins():
        install_package(pkg_dir, develop=develop)


def uninstall_plugins():
    for pkg_name, pkg_dir in find_plugins():
        uninstall_package(pkg_name)


if __name__ == '__main__':
    command = sys.argv[1]

    if command == 'install':
        create_sdists()
        install_plugins()
        #create_local_settings()

    elif command == 'develop':
        install_plugins(develop=True)
        #create_local_settings()

    elif command == 'uninstall':
        uninstall_plugins()

    else:
        show_help()


