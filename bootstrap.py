#!/usr/bin/env python

import os
import sys
import subprocess

import pip


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(BASE_DIR, 'plugins')
SDIST_DIR = os.path.join(PLUGINS_DIR, 'sdist')
INDEX_NAME = os.path.join(PLUGINS_DIR, 'plugin_index.html')


def show_help():
    print "%s [install|uninstall]" % sys.argv[0]
    print 
    print "Install or remove all of the included Portal plugins."


def which_pip():
    os.system('which pip')
    print __file__
    #from IPython import embed; embed()


def create_index():
    """ Create a simple index file of packages. """
    with open(INDEX_NAME, 'w') as f:
        f.write('<html><head>\n')
        f.write('<title>Simple Index</title>\n')
        f.write('<meta name="api-version" value="2" />\n')
        f.write('</head><body>\n')
        for pkg_name, root in find_plugins():
            f.write('<a href="%s">%s</a><br/>\n' % (pkg_name, pkg_name))
        f.write('</body></html>\n')


def create_sdists():
    if not os.path.isdir(SDIST_DIR):
        os.mkdir(SDIST_DIR)

    for pkg_name, root in find_plugins():
        os.chdir(root)
        os.system('python setup.py sdist --dist-dir %s' % SDIST_DIR)


def install_package(path):
    """ pip install the package at `path`. """
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
    for root, dirs, files in os.walk(PLUGINS_DIR):
        #print root, dirs, files
        if 'setup.py' in files:
            dirs[:] = []
            pkg_name = os.path.basename(root)
            yield pkg_name, root


def install_plugins():
    uninstall_plugins()
    for pkg_name, pkg_dir in find_plugins():
        install_package(pkg_dir)


def uninstall_plugins():
    for pkg_name, pkg_dir in find_plugins():
        uninstall_package(pkg_name)


if __name__ == '__main__':

    if 'install' in sys.argv:
        create_sdists()
        install_plugins()
    elif 'uninstall' in sys.argv:
        uninstall_plugins()
    else:
        show_help()


