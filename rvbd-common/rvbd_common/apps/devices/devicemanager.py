# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import logging
import threading

from rvbd.common import UserAuth
from rvbd_common.apps.devices.models import Device

logger = logging.getLogger(__name__)

lock = threading.Lock()


class DeviceManager(object):
    # map of active devices by datasource_id
    devices = {}

    @classmethod
    def clear(cls, device_id=None):
        if device_id and device_id in cls.devices:
            del cls.devices[device_id]
        else:
            cls.devices = {}

    @classmethod
    def get_device(cls, device_id):
        ds = Device.objects.get(id=device_id)

        with lock:
            if ds.id not in cls.devices:
                import rvbd_common.apps.datasource.modules
                module = rvbd_common.apps.datasource.modules.__dict__[ds.module]
                create_func = module.new_device_instance

                logger.debug("Creating new Device: %s(%s:%s)" % (ds.module,
                                                                 ds.host,
                                                                 ds.port))
                cls.devices[ds.id] = create_func(host=ds.host, port=ds.port,
                                                 auth=UserAuth(ds.username,
                                                               ds.password))
        return cls.devices[ds.id]

    @classmethod
    def list_modules(cls):
        """ Returns list of modules which have 'new_device_instance'
            function defined.
        """
        modules = []
        import rvbd_common.apps.datasource.modules
        for k, v in rvbd_common.apps.datasource.modules.__dict__.iteritems():
            if hasattr(v, 'new_device_instance'):
                modules.append(k)
        return modules
