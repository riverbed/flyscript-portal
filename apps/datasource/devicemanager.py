# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import logging
from rvbd.common import UserAuth
logger = logging.getLogger('report')

class DeviceManager:
    # map of active devices by datasource_id
    devices = {}

    @classmethod
    def register(cls, dev_class):
        cls.device_class[dev_class.__name__] = dev_class
        
    @classmethod
    def get_device(cls, device_id):
        from apps.datasource.models import Device
        ds = Device.objects.get(id=device_id)
        if ds.id not in cls.devices:
            import apps.datasource.datasource
            create_func = apps.datasource.datasource.__dict__[ds.sourcetype].DeviceManager_new
            
            logger.debug("Creating new Device: %s(%s:%s)" % (ds.sourcetype, ds.host, ds.port))
            cls.devices[ds.id] = create_func(host=ds.host, port=ds.port,
                                             auth=UserAuth(ds.username,
                                                           ds.password))
        return cls.devices[ds.id]

