# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import os

from project.utils import Importer

# portions and concepts used from sentry project:
# https://getsentry.com/welcome/


class PluginMount(type):
    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if IPlugin in bases:
            return new_cls
        if not new_cls.title:
            new_cls.title = new_cls.__name__
        if not new_cls.slug:
            new_cls.slug = new_cls.title.replace(' ', '-').lower()
        return new_cls


class IPlugin(object):
    """ Plugin base class. Should not be inherited from directly.
    """
    # Generic plugin metadata
    title = None
    slug = None
    description = None
    version = None
    author = None
    plugin_url = None

    # list of dependencies for this plugin
    dependencies = []

    # Global enabled state
    enabled = True
    can_disable = True

    # Plugin components
    reports = []        # list of report module directories
    libraries = []      # list of library directories
    datasources = []    # list of datasource directories
    devices = []        # list of device directories

    _reports_loaded = False

    def is_enabled(self):
        """ Returns boolean if this plugin is enabled. """
        return self.enabled or not self.can_disable

    def _get_sources(self, paths):
        import inspect
        import pkgutil

        module_name = self.__module__.rsplit('.', 1)[0]

        class_file = inspect.getfile(self.__class__)
        module_path = os.path.dirname(class_file)
        sourcepaths = [os.path.join(module_path, sdir) for sdir in paths]

        for instance, source_name, _ in pkgutil.iter_modules(sourcepaths):
            # append tuple of source_name, pkg_name
            source_path = instance.path
            rel_source_path = os.path.relpath(source_path, module_path)
            pkg_name = '.'.join([module_name,
                                 '.'.join(rel_source_path.split(os.path.sep)),
                                 source_name])
            yield (source_name, pkg_name)

    def get_reports(self):
        """ Returns list of library modules. """
        return self._get_sources(self.reports)

    def get_libraries(self):
        """ Returns list of library modules. """
        return self._get_sources(self.libraries)

    def get_datasources(self):
        """ Returns list of library modules. """
        return self._get_sources(self.datasources)

    def get_devices(self):
        """ Returns list of device modules. """
        return self._get_sources(self.devices)

    def load_reports(self):
        if self.reports and self.is_enabled():
            importer = Importer()

            for report_name, pkg_name in self.get_reports():
                importer.import_file(report_name, pkg_name)
            self._reports_loaded = True


class Plugin(IPlugin):
    """ Portal plugin class for subclassing. """
    __metaclass__ = PluginMount
