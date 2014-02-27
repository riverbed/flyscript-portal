#!/usr/bin/env python
"""
rvbd-portal-sample
==================

This plugin serves as a sample for building plugins.  See the
README for instructions.

Replace this text with a longer description of what the
plugin does.

"""
from setuptools import setup, find_packages

# Update 'sample' in the name to reflect your plugin
PLUGIN_NAME = 'rvbd-portal-sample'
# Update the version each time you make a new release
PLUGIN_VERSION = '0.1'

tests_require = []

install_requires = [
    'Django>=1.5.1,<1.6',
    # Add any special package requirements here
]

LICENSE = """\
Copyright (c) 2013 Riverbed Technology, Inc.

This software is licensed under the terms and conditions of the
MIT License set forth at:

https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").

This software is distributed "AS IS" as set forth in the License.
"""

setup(
    name=PLUGIN_NAME,
    version=PLUGIN_VERSION,

    # Update the following as needed
    author='Riverbed Technology',
    author_email='eng-github@riverbed.com',
    url='',
    description='A sample plugin for FlyScript Portal',
    long_description=__doc__,
    license=LICENSE,

    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=None,
    test_suite='',
    include_package_data=True,
    entry_points={
        'portal.plugins': [
            'sample = rvbd_portal_sample.plugin:Plugin'
            #'sample = rvbd_portal_sample.plugin:Plugin'
        ],
    },

    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
