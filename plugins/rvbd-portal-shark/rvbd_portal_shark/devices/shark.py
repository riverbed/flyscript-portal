# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd.shark import Shark


def new_device_instance(*args, **kwargs):
    # Used by DeviceManger to create a Shark instance
    shark = Shark(*args, **kwargs)
    return shark
