# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from rvbd.common.utils import RDictObject

class Options(RDictObject):
    _default = None
    _required = None
    
    def __init__(self, dict=None, **kwargs):
        #print "init: %s / %s" % (dict, kwargs)
        super(Options, self).__init__()
        self.apply_dict(self._default)
        self.apply_dict(dict)
        self.apply_dict(kwargs)

        if self._required is not None:
            for key in self._required:
                if self.__getattr__(key) is None:
                    raise KeyError("Required key not specified: %s" % '.'.join(key.split("__")))

    def __getattr__(self, key):
        if key[0] == '_':
            return object.__getattr__(self, key)

        # Treat "__" as a separator like a '.'
        #   so x.a__b ==> x.a.b
        keyparts = key.split("__")

        obj = self
        for k in keyparts:
            #print "looking at %s" % k
            if (not isinstance(obj, dict)) or (k not in obj):
                raise AttributeError(key)
            obj = obj[k]

        return obj
    
    def __setattr__(self, key, value):
        #print "setattr: self <<%s>> : setattr(%s => %s)" % (str(self), key, value)
        # Turn "obj.<key> = <value>" into "obj['<key>'] = <value>
        if key[0] == '_':
            # Treat keys starting with an underscore as normal attributes
            return object.__setattr__(self, key, value)

        # Treat "__" as a separator like a '.'
        #   so x.a__b ==> x.a.b
        keyparts = key.split("__")

        obj = self
        for key in keyparts[:-1]:
            if ((not isinstance(obj, dict)) or
                ((obj._default is not None) and (key not in obj._default))):
                raise KeyError("Invalid key: '%s'" % key)

            if (key not in obj) or (not isinstance(obj[key], dict)):
                obj[key] = Options()
                if obj._default is not None:
                    obj[key]._default = obj._default[key]

            obj = obj[key]

        key = keyparts[-1]

        if ((not isinstance(obj, dict)) or
            ((obj._default is not None) and (key not in obj._default))):
            raise KeyError("Invalid key: '%s'" % key)

        if isinstance(value, dict):
            obj[key] = Options(dict=value)
            if obj._default:
                obj[key]._default = obj._default[key]
        else:
            #print ("...setatter: %s => %s" % (key, value))
            obj[key] = value
            
def Test():
    class WidgetOptions(Options):
        _default = { 'width': None,
                     'height': None,
                     'scroll' : { 'vertical': True,
                                  'horizontal': False }
                     }
        _required = ['width', 'height']

    wo = WidgetOptions(width=6, scroll__vertical=3)

    
