#!/usr/bin/env python
"""
rvbd_portal
==========

Core apps for Riverbed FlyScript Portal

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
    name='rvbd-portal',
    version='0.1',

    author='Riverbed Technology',
    author_email='eng-github@riverbed.com',
    url='',
    description='Core apps for FlyScript Portal',
    long_description=__doc__,
    license=LICENSE,

    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=None,
    test_suite='',
    include_package_data=True,

    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
