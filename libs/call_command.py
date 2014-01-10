# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

from optparse import NO_DEFAULT

from django.core.management import get_commands, load_command_class
from django.core.management.base import BaseCommand, CommandError, handle_default_options

def call_command(name, *args, **options):
    """
    Calls the given command, with the given options and args/kwargs.

    This is a variant of the Django version that uses create_parser()
    instead of relying on option_list to get default values.

    """
    # Load the command object.
    try:
        app_name = get_commands()[name]
    except KeyError:
        raise CommandError("Unknown command: %r" % name)

    if isinstance(app_name, BaseCommand):
        # If the command is already loaded, use it directly.
        klass = app_name
    else:
        klass = load_command_class(app_name, name)

    parser = klass.create_parser(app_name, app_name)

    defaults = {}
    groups = [parser]
    if parser.option_groups:
        groups.extend(parser.option_groups)

    for group in groups:
        for opt in group.option_list:
            if opt.dest is None:
                continue
            if opt.default is NO_DEFAULT:
                defaults[opt.dest] = None
            else:
                defaults[opt.dest] = opt.default

    defaults.update(options)
    return klass.execute(*args, **defaults)
