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
from django.forms.util import from_current_timezone
from django.core.files.uploadedfile import UploadedFile
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.forms.widgets import FileInput, FILE_INPUT_CONTRADICTION, TextInput
from django.forms import widgets

from rvbd.common import datetime_to_seconds, parse_timedelta, timedelta_total_seconds

from apps.datasource.models import Criteria, TableField

import logging
logger = logging.getLogger(__name__)

DURATIONS = ('1 min', '15 min', '1 hour',
             '2 hours', '4 hours', '12 hours',
             '1 day', '1 week', '4 weeks')

class CriteriaError(Exception):
    """ Exception raised when a problem resolving criteria occurs. """
    pass

class CriteriaTemplateError(CriteriaError):
    pass

class CriteriaPostProcessError(CriteriaError):
    pass

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

class FileSelectField(forms.Field):
    def to_python(self, data):
        if data in validators.EMPTY_VALUES:
            return None

        if isinstance(self.widget, TextInput):
            return data

        elif isinstance(self.widget, FileInput):

            # UploadedFile objects should have name and size attributes.
            try:
                file_name = data.name
                file_size = data.size
            except AttributeError:
                raise ValidationError(self.error_messages['invalid'])

            if not file_name:
                raise ValidationError(self.error_messages['invalid'])

            # look for uploaded files, save them off to another
            # temporary file and return the path for use in JSON
            # consumers of this file will need to clean them up
            # TODO this will be replaced by the File Storage App
            newtemp = tempfile.NamedTemporaryFile(delete=False)
            data.seek(0)
            shutil.copyfileobj(data, newtemp)
            data.close()
            newtemp.close()
            return newtemp.name
        else:
            raise ValidationError('Unsupported widget source: %s' % str(self.widget))

        
class DateTimeField(forms.DateTimeField):
    
    """ Field that takes a date/time string and parses it to a datetime object. """
    
    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            return None

        if isinstance(value, list):
            # This came from SplitDateTimeWidget so the value is two strings
            value = ' '.join(value)
            
        if isinstance(value, str) or isinstance(value, unicode):
            try:
                v = dateutil.parser.parse(value, tzinfos=all_timezones_map())
            except:
                raise ValidationError('Invalid date/time string: %s' % value)
            
            return from_current_timezone(v)

        if isinstance(value, datetime.datetime):
            return from_current_timezone(value)

        if isinstance(value, datetime.date):
            result = datetime.datetime(value.year, value.month, value.day)
            return from_current_timezone(result)

        raise ValidationError('Unknown data/time field value type: %s' % type(value))
            
class DurationWidget(forms.MultiWidget):

    def __init__(self, 
                 choices=[(60, '1 minute'),
                          (60*15, '15 minutes'),
                          (60*60, 'Hour'),
                          (60*60*6, '6 Hour')],
                 **kwargs):
        self.choices = choices
        split_widgets = [widgets.Select(choices=choices),
                         widgets.TextInput()]
        super(DurationWidget, self).__init__(split_widgets)

    def decompress(self, value):
        if isinstance(value, str) or isinstance(value, unicode):
            value = timedelta_total_seconds(parse_timedelta(value))
            
        if value:
            m = [v for v in self.choices if v[0] == value]
            if len(m) == 1:
                return m[0]
            else:
                return [0, '%d min' % (value / 60)]

        return [None, None]

class DurationField(forms.ChoiceField):
    """ Field that takes a duration string and parses it to a timedelta object. """

    def __init__(self, **kwargs):
        self._special_values = kwargs.pop('special_values', None)
        initial = kwargs.pop('initial', None)
        if (  (initial is not None) and
              (self._special_values is None or (initial not in self._special_values))):
            initial_td = parse_timedelta(initial)

            m = None
            for v,label in kwargs['choices']:
                if (self._special_values is not None and v in self._special_values):
                    continue
                if parse_timedelta(v) == initial_td:
                    m = v
                    break
            if m:
                initial = v
            else:
                raise KeyError('Initial duration is invalid: %s' % initial)
        super(DurationField, self).__init__(initial=initial, **kwargs)
              
    def to_python(self, value):
        if value in validators.EMPTY_VALUES:
            v = None
        elif self._special_values and value in self._special_values:
            v = value
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
         #field_kwargs = { 'widget': DurationWidget },
         field_kwargs = { 'choices': zip(DURATIONS, DURATIONS) },
         required=False))
    duration.save()
    obj.fields.add(duration)


def fields_add_resolution(obj, initial=None,
                          resolutions= [('1min', '1 minute'),
                                        ('15min', '15 minutes'),
                                        ('hour', 'Hour'),
                                        ('6hour', '6 Hour')],
                          special_values=None
                          ):

    field = TableField(keyword = 'resolution',
                       label = 'Data Resolution',
                       field_cls = DurationField,
                       field_kwargs = { 'choices' : resolutions,
                                        'special_values': special_values },
                       initial=initial)
    field.save()
    obj.fields.add(field)


class TableFieldForm(forms.Form):
    """ Form built from a set of TableFields.
    """
    # css definitions
    error_css_class = 'text-error'

    # special hidden field definitions
    ignore_cache = forms.BooleanField(required=False, widget=forms.HiddenInput)
    debug = forms.BooleanField(required=False, widget=forms.HiddenInput)
    
    def __init__(self, fields, use_widgets=True, hidden_fields=None, include_hidden=False, **kwargs):
        """ Initialize a TableFieldForm for the given set of table.

        :param fields: dict of id to TableField

        :param use_widgets: if True (default) include UI-style widgets,
            otherwise (False) use only TextInput (suitable for command-line)

        Standard Form arguments `data` and `files` should be used
        as kwargs instead of passing as positional args.
            
        """

        if ('data' in kwargs):
            # Make a copy of data as we may change it below
            kwargs['data'] = copy.copy(kwargs['data'])

        super(TableFieldForm, self).__init__(**kwargs)

        self._tablefields = fields
        self._use_widgets = use_widgets
        self._hidden_fields = hidden_fields
        
        for field_id, field in fields.iteritems():
            if include_hidden or not (field.hidden or
                                      (hidden_fields and
                                       field.keyword in hidden_fields)):
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

        if not self._use_widgets:
            fkwargs['widget'] = TextInput

        for k in ['label', 'required', 'help_text', 'initial']:
            fkwargs[k] = getattr(field, k)

        f = field.pre_process_func
        if f is not None:
            f.function(field, fkwargs, f.params)

        self.fields[field_id] = field_cls(**fkwargs)

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

        data = copy.copy(self.initial)
        for k,v in self.cleaned_data.iteritems():
            if k in (self._hidden_fields or []):
                data[k] = self.fields[k].clean(self._tablefields[k].initial)
            else:
                data[k] = v
        criteria = Criteria(**data)
        
        # Since the form is valid, propagate values down from
        # parent TableFields down to thier children

        fieldset = self._tablefields.values()
        fieldset_keywords = [f.keyword for f in fieldset]

        # List of fields that are still unset after this iteration
        unprocessed_fields = copy.copy(fieldset)
        processed_keywords = set()

        # The fieldset is the *complete* list of fields that must
        # end up in the criteria.  Any "hidden" fields (TableField.hidden)
        # will not show up in the cleaned_data and must be filled in either
        # by post_process_template or the post_process_function.
        #
        # Iterate until all fields in the fieldset show up in the criteria
        while unprocessed_fields:
            next_field = None

            # Iterate through the fieldset (note, this is initially all fields, but
            # after this loop it gets set to unprocessed_fields
            for field in unprocessed_fields:

                if field.parent_keywords and not set(field.parent_keywords).issubset(processed_keywords):
                    # This field still has unprocessed parents
                    continue

                next_field = field
                break

            if next_field is None:
                raise CriteriaError(('Failed to resolve all criteria, remaining fields ' +
                                     'may have circular dependencies: %s') %
                                    ([f.keyword for f in unprocessed_fields]))
            
            if field.post_process_template:
                # Resolve the fields criteria value by the <string>.format() function
                # using a template.
                try:
                    criteria[field.keyword] = field.post_process_template.format(**criteria)
                except:
                    raise (CriteriaTemplateError
                           ("Failed to resolve field %s template: %s" %
                            (field.keyword, field.post_process_template)))

            elif field.post_process_func is not None:
                # Call the post process function
                f = field.post_process_func
                try:
                    f.function(field, criteria, f.params)
                except Exception as e:
                    raise (CriteriaPostProcessError
                           ('Field %s function %s raised an exception: %s %s' %
                            (field, f.function, type(e), e)))

                if field.keyword not in criteria:
                    raise (CriteriaPostProcessError
                           ('Field %s function %s failed to set criteria.%s value' %
                            (field, f.function, field.keyword)))
            elif field.keyword not in criteria:
                raise CriteriaError('Field %s has no value and no post-process hooks' %
                                    field)

            unprocessed_fields.remove(field)
            processed_keywords.add(field.keyword)

                
        return criteria

    def apply_timezone(self, tzinfo):
        """ Apply `tzinfo` as the timezone of any naive datetime objects. """
        if not self.is_valid():
            raise ValidationError("Form data is not valid")

        for k,v in self.cleaned_data.iteritems():
            if isinstance(v, datetime.datetime) and v.tzinfo is None:
                self.cleaned_data[k] = v.replace(tzinfo = tzinfo)

