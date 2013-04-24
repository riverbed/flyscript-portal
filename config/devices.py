# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import Device 
from apps.datasource.modules.shark import setup_capture_job

#### Customize devices and authorization here

# The name="profiler" is used in all reports scripts.  If you change the name,
# you'll need to replace it at the top of each report script
PROFILER = Device(name="profiler", 
                  module="profiler",
                  host="fill.in.profiler.host.or.ip",
                  port=443,
                  username="<username>",
                  password="<password>")
PROFILER.save()

# The name="shark1" is used in all reports scripts.  If you change the name,
# you'll need to replace it at the top of each report script
SHARK1 = Device(name="shark1",
                module="shark",
                host="fill.in.profiler.host.or.ip",
                port=443,
                username="<username>",
                password="<password>")

SHARK1.save()


# Shark capture view setup
#
# The configuration files use 'flyscript-portal' as the configured viewname
# so this step just makes sure the view is active on the Shark
# If a different view name is desired (perhaps an existing view),
# change the SHARK_CAPTURE_JOB_NAME below, as well as all of the
# references in the reports/*.py files.
#
SHARK_CAPTURE_JOB_NAME = 'flyscript-portal'
SHARK_CAPTURE_JOB_SIZE = '10%'                      # absolute bytes or percentages work here

setup_capture_job(SHARK1.id, SHARK_CAPTURE_JOB_NAME, SHARK_CAPTURE_JOB_SIZE)
