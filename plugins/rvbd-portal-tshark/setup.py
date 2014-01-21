#!/usr/bin/env python
"""
rvbd-portal-tshark
==========

A datasource plugin for FlyScript Portal to create tshark tables

"""
from setuptools import setup, find_packages


tests_require = []

install_requires = [
    'Django>=1.5.1,<1.6',
    # flyscript-portal should be here too
]

LICENSE = """\
Copyright (c) 2013 Riverbed Technology, Inc.

This software is licensed under the terms and conditions of the
MIT License set forth at:

https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").

This software is distributed "AS IS" as set forth in the License.
"""

setup(
    name='rvbd-portal-tshark',
    version='0.1',
    author='Riverbed Technology',
    author_email='eng-github@riverbed.com',
    url='',
    description='A datasource plugin for FlyScript Portal '
                'providing tshark device interfaces',
    long_description=__doc__,
    license=LICENSE,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=None,
    test_suite='',
    include_package_data=True,
    entry_points={
        'portal.plugins': [
            'tshark = rvbd_portal_tshark.plugin:TSharkPlugin'
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
