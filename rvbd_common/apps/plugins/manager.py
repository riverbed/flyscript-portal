# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging


# portions and concepts used from sentry project:
# https://getsentry.com/welcome/

class PluginManager(object):
    """ Instance manager of registered plugins.
    """

    # tailored merge of sentry.plugins.base.PluginManager and
    #                   sentry.utils.managers.InstanceManager

    def __init__(self, class_list=None, instances=True):
        if class_list is None:
            class_list = []
        self.instances = instances
        self.update(class_list)

    def __iter__(self):
        return iter(self.all())

    def __len__(self):
        return sum(1 for i in self.all())

    def get_class_list(self):
        return self.class_list

    def add(self, class_path):
        self.cache = None
        self.class_list.append(class_path)

    def remove(self, class_path):
        self.cache = None
        self.class_list.remove(class_path)

    def update(self, class_list):
        self.cache = None
        self.class_list = class_list

    def _all(self):
        """ Returns a list of cached instances. """
        class_list = list(self.get_class_list())
        if not class_list:
            self.cache = []
            return []

        if self.cache is not None:
            return self.cache

        results = []
        for cls_path in class_list:
            module_name, class_name = cls_path.rsplit('.', 1)
            try:
                module = __import__(module_name, {}, {}, class_name)
                cls = getattr(module, class_name)
                if self.instances:
                    results.append(cls())
                else:
                    results.append(cls)
            except Exception:
                logger = logging.getLogger(__name__)
                logger.exception('Unable to import %s', cls_path)
                continue
        self.cache = results

        return results

    def enabled(self):
        for plugin in sorted(self._all(), key=lambda x: x.title):
            if not plugin.is_enabled():
                continue
            yield plugin

    def all(self):
        for plugin in sorted(self._all(), key=lambda x: x.title):
            yield plugin

    def get(self, slug):
        for plugin in self.all():
            if plugin.slug == slug:
                return plugin
        raise KeyError(slug)

    def register(self, cls):
        self.add('%s.%s' % (cls.__module__, cls.__name__))
        return cls

    def unregister(self, cls):
        self.remove('%s.%s' % (cls.__module__, cls.__name__))
        return cls


plugins = PluginManager()
register = plugins.register
unregister = plugins.unregister
