# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import json

class Options(object):
    def __init__(self, *args, **kwargs):
        pass

    def encode(self):
        return json.dumps(self.__dict__)

    @classmethod
    def decode(cls, obj):
        if obj != '""':
            return cls(**json.loads(obj))
        return cls()
    

