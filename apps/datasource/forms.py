# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import shutil
import tempfile
import dateutil
import datetime
import copy
import pytz

from django import forms
from django.utils.datastructures import SortedDict
from django.core.files.uploadedfile import UploadedFile
from django.core import validators
from django.core.exceptions import ValidationError

from rvbd.common import datetime_to_seconds, parse_timedelta, timedelta_total_seconds

from apps.datasource.models import Criteria, TableField

import logging
logger = logging.getLogger(__name__)

DURATIONS = ('Default', '1 min', '15 min', '1 hour',
             '2 hours', '4 hours', '12 hours',
             '1 day', '1 week', '4 weeks')

# Map of all possible timezone names to tzinfo structures
ALL_TIMEZONES_MAP = None
def all_timezones_map():
    global ALL_TIMEZONES_MAP
    if ALL_TIMEZONES_MAP is None:
        ALL_TIMEZONES_MAP = dict((n,pytz.timezone(n)) for n in pytz.all_timezones)
    return ALL_TIMEZONES_MAP

class DateWidget(forms.DateInput):
    """ Custom DateWidget
    """

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'date'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(DateWidget, self).__init__(attrs=final_attrs, format=format)

    def render(self, name, value, *args, **kwargs):
        msg = '''
        {0} <span id="datenow" class="icon-calendar" title="Set date to today"> </span>
        <script type="text/javascript">
              $("#id_{name}").datepicker({{
                 format: "mm/dd/YY",
                 defaultDate: +2, 
                 autoclose: true
              }});
              $("#id_{name}").datepicker("setDate", new Date());
              $("#datenow").click(function() {{ $("#id_{name}").datepicker("setDate", new Date()); }});
          </script>
          '''
        return msg.format(super(DateWidget, self).render(name, value, *args, **kwargs), name=name)


class TimeWidget(forms.TimeInput):
    """ Custom TimeWidget for Reports
    """

    def __init__(self, attrs=None, format=None):
        final_attrs = {'class': 'time'}
        if attrs is not None:
            final_attrs.update(attrs)
        super(TimeWidget, self).__init__(attrs=final_attrs, format=format)

    def render(self, name, value, *args, **kwargs):
        msg = '''
        {0} <span id="timenow" class="icon-time" title="Set time/date to now"> </span> 
        <script type="text/javascript">
              $("#id_{name}").timepicker({{ 
                 step: 15, 
                 scrollDefaultNow:true,
                 timeFormat:"g:i a"
              }});
              $("#timenow").click(function() {{ 
                 $("#id_{name}").timepicker("setTime", new Date()); 
              }});
              $("#id_{name}").timepicker("setTime", new Date());
        </script>
        '''
        return msg.format(super(TimeWidget, self).render(name, value, *args, **kwargs), name=name)

class ReportSplitDateTimeWidget(forms.SplitDateTimeWidget):
    """ A SplitDateTime Widget that uses overridden Report widgets
    """
    def __init__(self, attrs=None):
        split_widgets = [DateWidget, TimeWidget]
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        forms.MultiWidget.__init__(self, split_widgets, attrs)

    def value_from_datadict(self, data, files, name):
        v = super(ReportSplitDateTimeWidget, self).value_from_datadict(data, files, name)
        v = ' '.join(v)
        return v

    def decompress(self, value):
        logger.debug("ReportSplitDateTimeWidget.decompress: %s" % (value))
        if value:
            return value.split(" ", 1)
        else:
            return [None, None]
        
class DateTimeField(forms.DateTimeField):
    """ Field that takes a date/time string and parses it to a datetime object. """
    
    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            return None
        try:
            v = dateutil.parser.parse(value, tzinfos=all_timezones_map())
        except:
            raise ValidationError('Invalid date/time string: %s' % value)
            
        return v
            
class DurationField(forms.ChoiceField):
    """ Field that takes a duration string and parses it to a timedelta object. """

    def to_python(self, value):
        if value in validators.EMPTY_VALUES or value == 'Default':
            v = None
        else:
            try:
                v = parse_timedelta(value)
            except:
                raise ValidationError('Invalid duration string: %s' % value)

        logger.debug("DurationField.to_python: %s" % v)
        return v

    def validate(self, value):
        logger.debug("DurationField.validate: %s" % value)
        pass
    
def fields_add_time_selection(obj, initial_duration=None):
    #starttime = TableField(keyword = 'starttime',
    #                            label = 'Start Time',
    #                            field_cls = DateTimeField,
    #                            field_kwargs = { 'widget' : ReportSplitDateTimeWidget },
    #                            required=False)
    #starttime.save()
    #obj.criteria.add(starttime)

    endtime = TableField(keyword = 'endtime',
                         label = 'End Time',
                         field_cls = DateTimeField,
                         field_kwargs = { 'widget' : ReportSplitDateTimeWidget },
                         required=False)
    endtime.save()
    obj.fields.add(endtime)

    duration = (
        TableField
        (keyword = 'duration',
         label = 'Duration',
         initial = initial_duration,
         field_cls = DurationField,
         field_kwargs = { 'choices': zip(DURATIONS, DURATIONS) },
         help_text = ("Report duration.  A value of 'Default' means use the " +
                      "default duration defined for each embedded table.  "),
         required=False))
    duration.save()
    obj.fields.add(duration)


class TableFieldForm(forms.Form):
    """ Form built from a set of TableFields.
    """
    # css definitions
    error_css_class = 'text-error'

    # special hidden field definitions
    ignore_cache = forms.BooleanField(required=False, widget=forms.HiddenInput)
    debug = forms.BooleanField(required=False, widget=forms.HiddenInput)
    
    def __init__(self, fields, use_widgets=True, **kwargs):
        """ Initialize a TableFieldForm for the given set of table.

        :param fields: dict of id to TableField

        :param use_widgets: if True (default) include UI-style widgets,
            otherwise (False) use only CharField (suitable for command-line)

        Standard Form arguments `data` and `files` should be used
        as kwargs instead of passing as positional args.
            
        """

        if ('data' in kwargs):
            # Make a copy of data as we may change it below
            kwargs['data'] = copy.copy(kwargs['data'])

        super(TableFieldForm, self).__init__(**kwargs)

        self._tablefields = fields
        self._use_widgets = use_widgets
        
        for field_id, field in fields.iteritems():
            if not field.hidden:
                self.add_field(field_id, field)
                
    def add_field(self, field_id, field):
        if field_id in self.fields:
            # Already added this field
            return

        field_cls = field.field_cls or forms.CharField

        if field.field_kwargs is not None:
            fkwargs = copy.copy(field.field_kwargs)
        else:
            fkwargs = {}

        if not self._use_widgets and 'widget' in fkwargs:
            del fkwargs['widget']

        for k in ['label', 'required', 'initial', 'help_text']:
            fkwargs[k] = getattr(field, k)
        
        f = field.pre_process_func
        if f is not None:
            f.function(field, fkwargs, f.params)

        self.fields[field_id] = field_cls(**fkwargs)
        self.initial[field_id] = fkwargs['initial']

    def as_text(self):
        """ Return certain field values as a dict for simple json parsing
        """
        result = {}

        for k, v in self.cleaned_data.iteritems():
            
            if isinstance(v, datetime.datetime):
                result[k] = v.isoformat()
            elif isinstance(v, datetime.timedelta):
                result[k] = str(timedelta_total_seconds(v)) + " seconds"
            elif isinstance(v, UploadedFile):
                # look for uploaded files, save them off to another
                # temporary file and return the path for use in JSON
                # consumers of this file will need to clean them up
                # TODO this will be replaced by the File Storage App
                newtemp = tempfile.NamedTemporaryFile(delete=False)
                v.seek(0)
                shutil.copyfileobj(v, newtemp)
                v.close()
                newtemp.close()
                result[k] = newtemp.name
            else:
                result[k] = v

        return result

    def criteria(self):
        """ Return a Criteria object based on this form data. """
        
        if not self.is_valid():
            raise ValidationError("Form data is not valid")

        criteria = Criteria(**self.cleaned_data)

        # Since the form is valid, propagate values down from
        # parent TableFields down to thier children

        fieldset = self._tablefields.values()
        while fieldset:
            field = fieldset.pop()
                
            for parent in field.parents.all():
                if not parent.keyword in criteria:
                    # this parent's keyword hasn't been computed yet -- make sure
                    # we didn't get an invalid relationship
                    if parent.keyword not in fieldset:
                        raise KeyError("Child field %s depends on parent %s, " +
                                       "but parent didn't show up in fieldset" %
                                       (child.keyword, parent.keyword))
                    # add this on to the end for reprocessing
                    fieldset.append(field)
                    continue

            if field.post_process_template:
                try:
                    criteria[field.keyword] = field.post_process_template.format(**criteria)
                except:
                    raise KeyError("Failed to resolve field %s template: %s" %
                                   (field.keyword, field.template))
                                   
            else:
                f = field.post_process_func
                if f is not None:
                    f.function(field, criteria, f.params)
                    print "criteria %s" % criteria
                
        return criteria

    def apply_timezone(self, tzinfo):
        """ Apply `tzinfo` as the timezone of any naive datetime objects. """
        if not self.is_valid():
            raise ValidationError("Form data is not valid")

        for k,v in self.cleaned_data.iteritems():
            if isinstance(v, datetime.datetime) and v.tzinfo is None:
                self.cleaned_data[k] = v.replace(tzinfo = tzinfo)

