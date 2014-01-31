#!/usr/bin/env python

import os
import sys
import subprocess


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(BASE_DIR, 'plugins')
SDIST_DIR = os.path.join(PLUGINS_DIR, 'sdist')

LOCAL_SETTINGS = os.path.join(BASE_DIR, 'project', 'settings_local.py')

LOCAL_SETTINGS_CONTENT = """
# Optionally add additional applications specific to this webserver
LOCAL_APPS = None

# Add other settings customizations below, which will be local to this
# machine only, and not recorded by git. This could include database or
# other authentications, LDAP settings, or any other overrides.

# For example LDAP configurations, see the file
# `project/ldap_example.py`.
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
        create_local_settings()

    elif command == 'develop':
        install_plugins(develop=True)
        create_local_settings()

    elif command == 'uninstall':
        uninstall_plugins()

    else:
        show_help()
