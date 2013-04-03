# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from apps.datasource.models import *

#### Customize devices and authorization here

tm08 = Device(name="tm08-1",
              module="profiler",
              host="tm08-1.lab.nbttech.com",
              port=443,
              username="admin",
              password="admin")
tm08.save()

v10 = Device(name="vdorothy10",
             module="shark",
             host="vdorothy10.lab.nbttech.com",
             port=443,
             username="admin",
             password="admin")
v10.save()

