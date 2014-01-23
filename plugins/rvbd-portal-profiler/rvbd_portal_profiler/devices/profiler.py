# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import rvbd.profiler


def new_device_instance(*args, **kwargs):
    # Used by DeviceManager to create a Profiler instance
    return rvbd.profiler.Profiler(*args, **kwargs)
