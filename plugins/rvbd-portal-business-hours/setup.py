#!/usr/bin/env python
"""
rvbd-portal-business-hours
==========

A plugin for FlyScript Portal to enable Business Hour reports

"""
from setuptools import setup, find_packages


tests_require = []

install_requires = [
    'Django>=1.5.1,<1.6',
    'rvbd-portal-profiler>=0.1',
    'rvbd-portal-profiler-devices>=0.1',
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
    name='rvbd-portal-business-hours',
    version='0.0.1',
    author='Riverbed Technology',
    author_email='eng-github@riverbed.com',
    url='',
    description='A business hours plugin for FlyScript Portal '
                'providing reports and support libraries',
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
            'business_hours = rvbd_portal_business_hours.plugin:BusinessHoursPlugin'
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
