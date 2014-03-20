#!/usr/bin/env python
"""
rvbd-portal-sharepoint
==========

A datasource plugin for FlyScript Portal to integrate Sharepoint data.

"""
from setuptools import setup, find_packages


tests_require = []

install_requires = [
    'Django>=1.5.1,<1.6',
    'sharepoint==0.3.2',
    'python-ntlm==1.0.1',
    'lxml>=3.3.0,<3.4.0',
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
    name='rvbd-portal-sharepoint',
    version='0.1',

    author='Riverbed Technology',
    author_email='eng-github@riverbed.com',
    url='',
    description='A datasource plugin for FlyScript Portal '
                'providing sharepoint device interfaces',
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
            'sharepoint = rvbd_portal_sharepoint.plugin:SharepointPlugin'
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
