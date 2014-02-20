#!/usr/bin/env python

import os
import sys
import subprocess


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(BASE_DIR, 'plugins')
SDIST_DIR = os.path.join(PLUGINS_DIR, 'sdist')

SETTINGS_DIR = os.path.join(BASE_DIR, 'project', 'settings')
ACTIVE_SETTINGS = os.path.join(SETTINGS_DIR, 'active.py')
DEV_SETTINGS = os.path.join(SETTINGS_DIR, 'development.py')
PROD_SETTINGS = os.path.join(SETTINGS_DIR, 'production.py')

ACTIVE_CONTENT = """
# This file indicates the default configuration to use.
# Initially, this pulls settings from the 'development.py' file,
# but that can be changed below.
#
# Alternate configurations may still be called with a '--settings'
# argument passed to the manage.py command.

from project.settings.development import *
"""

LOCAL_SETTINGS_CONTENT = """
from project.settings import *

# This file adds site specific options to the server settings
# To activate this file for use, include the following option as part of
# "manage.py" commands:
#   --settings=project.settings_local
#
# For example:
#   $ ./clean --reset --force --settings=project.settings_local

# Optionally add additional applications specific to this webserver

LOCAL_APPS = (
    # additional apps can be listed here
)
INSTALLED_APPS += LOCAL_APPS

# Configure alternate databases for development or production.  Leaving this
# section commented will default to the development sqlite database.

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',      # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
#        'NAME': os.path.join(PROJECT_ROOT, 'project.db'),  # Or path to database file if using sqlite3.
#        #'TEST_NAME': os.path.join(PROJECT_ROOT, 'test_project.db'),  # Or path to database file if using sqlite3.
#        'USER': '',                      # Not used with sqlite3.
#        'PASSWORD': '',                  # Not used with sqlite3.
#        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#    }
#}

# Add other settings customizations below, which will be local to this
# machine only, and not recorded by git. This could include database or
# other authentications, LDAP settings, or any other overrides.

# For example LDAP configurations, see the file
# `project/ldap_example.py`.
"""

SETTINGS = ((ACTIVE_SETTINGS, ACTIVE_CONTENT),
            (DEV_SETTINGS, LOCAL_SETTINGS_CONTENT),
            (PROD_SETTINGS, LOCAL_SETTINGS_CONTENT))


def show_help():
    print "%s [install|uninstall|develop|settings]" % sys.argv[0]
    print 
    print "Perform initial configuration and setup for server."
    print "Valid options:"
    print "`install` - install all packages to site-packages directory"
    print "`uninstall` - remove all portal packages from site-packages"
    print "`develop` - install packages in develop mode without dependencies"
    print "`settings` - just setup the default settings files"
    print "             optionally pass '--force' to overwrite existing files"
    sys.exit()


def which_pip():
    os.system('which pip')
    print __file__
    #from IPython import embed; embed()


def create_local_settings(force=False):
    """ Creates local settings configuration if none exists.
    """
    msg = []

    for fname, content in SETTINGS:
        if force or not os.path.exists(fname):
            with open(fname, 'w') as f:
                f.write(content)
            m = 'Local configuration file created: %s' % fname
            msg.append(m)

    if msg:
        print '*****'
        print '\n'.join(msg)
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
    try:
        command = sys.argv[1]
    except IndexError:
        show_help()

    if command == 'install':
        create_sdists()
        install_plugins()
        create_local_settings()

    elif command == 'develop':
        install_plugins(develop=True)
        create_local_settings()

    elif command == 'uninstall':
        uninstall_plugins()

    elif command == 'settings':
        create_local_settings(force=('--force' in sys.argv))

    else:
        show_help()
