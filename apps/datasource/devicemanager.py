# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import logging
import threading

from rvbd.common import UserAuth
logger = logging.getLogger(__name__)

lock = threading.Lock()

class DeviceManager:
    # map of active devices by datasource_id
    devices = {}

    @classmethod
    def clear(cls, device_id=None):
        if device_id and device_id in cls.devices:
            del cls.devices[device_id]
        else:
            cls.devices = {}

    @classmethod
    def register(cls, dev_class):
        cls.device_class[dev_class.__name__] = dev_class
        
    @classmethod
    def get_device(cls, device_id):
        from apps.datasource.models import Device
        ds = Device.objects.get(id=device_id)

        with lock:
            if ds.id not in cls.devices:
                import apps.datasource.modules
                create_func = apps.datasource.modules.__dict__[ds.module].DeviceManager_new

                logger.debug("Creating new Device: %s(%s:%s)" % (ds.module, ds.host, ds.port))
                cls.devices[ds.id] = create_func(host=ds.host, port=ds.port,
                                                 auth=UserAuth(ds.username,
                                                               ds.password))
        return cls.devices[ds.id]

