# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.


import inspect
import logging

from rvbd.common.jsondict import JsonDict

from django.db import models
from django.db.models import Max, Sum
from django.template.defaultfilters import slugify
from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.datastructures import SortedDict
from django.core.exceptions import ObjectDoesNotExist

from model_utils.managers import InheritanceManager
from rvbd_portal.apps.datasource.models import Table, Job, TableField

from rvbd_portal.libs.fields import PickledObjectField, SeparatedValuesField

logger = logging.getLogger(__name__)


class WidgetOptions(JsonDict):
    _default = {'key': None,
                'value': None,
                'axes': None}


def get_caller_name(current_module):
    """ Determine filename of calling function.
        Used to determine source of Report class definition.
    """
    frame = inspect.stack()[2]
    frm = frame[0]
    mod = inspect.getmodule(frm)
    del frm
    return mod.__name__


class Report(models.Model):
    """ Defines a Report as a collection of Sections and their Widgets. """
    title = models.CharField(max_length=200)
    position = models.IntegerField(default=0)
    enabled = models.BooleanField(default=True)

    slug = models.SlugField(unique=True)
    namespace = models.CharField(max_length=100, default='default')
    sourcefile = models.CharField(max_length=200)

    fields = models.ManyToManyField(TableField, null=True, blank=True)
    field_order = SeparatedValuesField(null=True,
                                       default=['starttime', 'endtime',
                                                'duration', 'filterexpr'],
                                       blank=True)
    hidden_fields = SeparatedValuesField(null=True, blank=True)

    # create an 'auto-load'-type report which uses default criteria
    # values only, and optionally set a refresh timer
    hide_criteria = models.BooleanField(default=False)
    reload_minutes = models.IntegerField(default=0)  # 0 means no reloads

    def __init__(self, *args, **kwargs):
        if 'sourcefile' not in kwargs:
            kwargs['sourcefile'] = get_caller_name(self)

        if 'namespace' not in kwargs:
            if kwargs['sourcefile'].startswith('config.'):
                kwargs['namespace'] = 'default'
            else:
                # sourcefile 'rvbd_portal_wireshark.reports.88_pcap_filefield'
                # will have namespace 'wireshark'
                ns = kwargs['sourcefile'].split('.')[0]
                ns = ns.replace('rvbd_portal_', '')
                kwargs['namespace'] = ns

        super(Report, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.sourcefile.split('.')[-1])
        super(Report, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title

    def collect_fields_by_section(self):
        """ Return a dict of all fields related to this report by section id.
        """

        # map of section id to field dict
        fields_by_section = {}

        # section id=0 is the "common" section
        fields_by_section[0] = SortedDict()
        if self.fields:
            report_fields = {}
            for f in self.fields.all():
                report_fields[f.keyword] = f

            fields_by_section[0].update(report_fields)

        # Pull in fields from each section (which may add fields to
        # the common as well)
        for s in Section.objects.filter(report=self):
            for section_id, fields in s.collect_fields_by_section().iteritems():
                if section_id not in fields_by_section:
                    fields_by_section[section_id] = fields
                else:
                    fields_by_section[section_id].update(fields)

        # Reorder fields in each section according to the field_order list
        new_fields_by_section = {}
        for i, fields in fields_by_section.iteritems():
            # fields_by_section will have the format:
            #   { 's17_duration' : TableField(keyword='duration'),
            #     's18_duration' : TableField(keyword='duration'), ...}
            # The field_order list is by keyword, not the <sectionid>_<keyword> format
            keywords_to_field_names = SortedDict()
            for (field_name,field) in fields_by_section[i].iteritems():
                keywords_to_field_names[field.keyword] = (field_name,field)

            ordered_field_names = SortedDict()
            # Iterate over the defined order list, which may not address all fields
            if self.field_order:
                for keyword in self.field_order:
                    if keyword in keywords_to_field_names:
                        pair = keywords_to_field_names[keyword]
                        ordered_field_names[pair[0]] = pair[1]
                        del keywords_to_field_names[keyword]

            # Preserve the order of any fields left
            for pair in keywords_to_field_names.values():
                ordered_field_names[pair[0]] = pair[1]

            new_fields_by_section[i] = ordered_field_names

        return new_fields_by_section

    def widgets(self):
        return Widget.objects.filter(section__in=Section.objects.filter(report=self)).order_by('id')


class Section(models.Model):
    """ Define a section of a report.

    Sections provide a means to control how fields and criteria are
    handled.  The critieria is a Criteria object filled in with values
    provided by the end user based on a set of TableFields.

    All tables (via Widgets) in the same section will all be passed
    the same run-time criteria.  The set of fields that a user may
    fill in for a section is a union of all TableFields of all tables
    in that section.  The union is based on the TableField keyword
    attribute, thus two tables that each define a TableField with the
    same keyword will share the same value in the resulting criteria
    object at run time.  The first TableField instance found for a
    given keyword is the actual object instance used for generating
    the UI form.

    If there are multiple sections, the section may be configured to
    either inherit fields from the report (SectionFieldMode.INHERIT)
    or to make the field specific to the section
    (SectionFieldMode.SECTION).

    Each section has a default mode that applies to all field
    keywords that are not called out explicitly.  If the section
    default mode is INHERIT, specific keywords can be set to SECTION
    by createing SectionFieldMode entries.

    """

    report = models.ForeignKey(Report)
    title = models.CharField(max_length=200, blank=True)
    position = models.IntegerField(default=0)
    fields = models.ManyToManyField(TableField, null=True)

    @classmethod
    def create(cls, report, title='', position=0,
               section_keywords=None,
               default_field_mode=None,
               keyword_field_modes=None):
        """ Create a Section of a report and define field modes.

        :param report: the report this section applies to

        :param title: section title to display

        :param position: relative position for ordering on display,
            if 0 (default), this will be added as the last
            section of the current report

        :param default_field_mode: the default mode for how to
            handle fields.  If None (default), INHERIT will be used

        :param keyword_field_modes: dict of keyword to mode to
            override the `default_field_mode`.  Each entry in this
            dict will result in a SectionFieldMode object

        """
        if position == 0:
            posmax = Section.objects.filter(report=report).aggregate(Max('position'))
            pos = (posmax['position__max'] or 0) + 1

        section = Section(report=report, title=title, position=position)
        section.save()

        critmode = SectionFieldMode(section=section,
                                    keyword='',
                                    mode=default_field_mode or SectionFieldMode.INHERIT)
        critmode.save()

        if section_keywords is not None:
            if not isinstance(section_keywords,list):
                section_keywords = [section_keywords]

            for keyword in section_keywords:
                critmode = SectionFieldMode(section=section,
                                            keyword=keyword,
                                            mode=SectionFieldMode.SECTION)
                critmode.save()

        if keyword_field_modes:
            for keyword, mode in keyword_field_modes.iteritems():
                critmode = SectionFieldMode(section=section,
                                            keyword=keyword,
                                            mode=mode)
                critmode.save()

        return section

    def collect_fields_by_section(self):
        # Gather up all fields
        fields = []

        # All fields attached to the section
        for f in self.fields.all().order_by('id'):
            fields.append(f)

        # All fields attached to any Widget's Tables
        for w in Widget.objects.filter(section=self):
            for t in w.tables.all():
                for f in t.fields.all().order_by('id'):
                    fields.append(f)

        fields_by_section = SortedDict()
        fields_by_section[0] = {}
        fields_by_section[self.id] = {}
        for f in fields:
            # Split fields into section vs common based on the field_mode
            # for each keyword
            if self.fields_mode(f.keyword) is SectionFieldMode.SECTION:
                # Section fields are prefixed with the section id
                # in the field map
                id = "__s%s_%s" % (self.id, f.keyword)
                if id not in fields_by_section[self.id]:
                    fields_by_section[self.id][id] = f
            else:
                id = f.keyword
                if id not in fields_by_section[0]:
                    fields_by_section[0][id] = f

        return fields_by_section

    def fields_mode(self, keyword):
        try:
            m = self.sectionfieldmode_set.get(keyword=keyword)
            return m.mode
        except ObjectDoesNotExist: pass

        try:
            m = self.sectionfieldmode_set.get(keyword='')
            return m.mode
        except ObjectDoesNotExist: pass

        return SectionFieldMode.INHERIT


class SectionFieldMode(models.Model):
    section = models.ForeignKey(Section)
    keyword = models.CharField(blank=True, max_length=200)

    INHERIT = 0
    SECTION = 1
    mode = models.IntegerField(default=INHERIT,
                               choices=((INHERIT, "Inherit"),
                                        (SECTION, "Section")))


class Widget(models.Model):
    """ Defines a UI widget and the source datatables
    """
    tables = models.ManyToManyField(Table)
    section = models.ForeignKey(Section)
    title = models.CharField(max_length=100)
    row = models.IntegerField()
    col = models.IntegerField()
    width = models.IntegerField(default=1)
    height = models.IntegerField(default=300)
    rows = models.IntegerField(default=-1)
    options = PickledObjectField()

    module = models.CharField(max_length=100)
    uiwidget = models.CharField(max_length=100)
    uioptions = PickledObjectField()

    objects = InheritanceManager()

    def __repr__(self):
        return '<Widget %s (%s)>' % (self.title, self.id)

    def __unicode__(self):
        return '<Widget %s (%s)>' % (self.title, self.id)

    def widgettype(self):
        return 'rvbd_%s.%s' % (self.module.split('.')[-1], self.uiwidget)

    def table(self, i=0):
        return self.tables.all()[i]

    def compute_row_col(self):
        rowmax = self.section.report.widgets().aggregate(Max('row'))
        row = rowmax['row__max']
        if row is None:
            row = 1
            col = 1
        else:
            widthsum = self.section.report.widgets().filter(row=row).aggregate(Sum('width'))
            width = widthsum['width__sum']
            if width + self.width > 12:
                row = row + 1
                col = 1
            else:
                col = width + 1
        self.row = row
        self.col = col

    def criteria_from_form(self, form):
        """ Extract POST style criteria data from form. """
        fields_by_section = self.section.report.collect_fields_by_section()

        common_fields = fields_by_section[0]
        section_fields = fields_by_section[self.section.id]

        # Reverse the process of adding the prefix to SECTION-level criteria.
        # If a field is in section_fields, the id has the prefix, just use
        # the original keyword in the returned fields
        fields = {}
        for k, v in form.as_text().iteritems():
            if k in common_fields:
                fields[common_fields[k].keyword] = v
            elif k in section_fields:
                fields[section_fields[k].keyword] = v
            elif k in ['debug', 'ignore_cache']:
                fields[k] = v

        return fields

    def collect_fields(self):
        # Gather up all fields
        fields = SortedDict()

        # All fields attached to the section's report
        for f in self.section.report.fields.all().order_by('id'):
            fields[f.keyword] = f

        # All fields attached to the section
        for f in self.section.fields.all().order_by('id'):
            fields[f.keyword] = f

        # All fields attached to any Widget's Tables
        for w in self.section.widget_set.all().order_by('id'):
            for t in w.tables.all():
                for f in t.fields.all().order_by('id'):
                    fields[f.keyword] = f

        return fields


class WidgetJob(models.Model):
    """ Query point for status of Jobs for each Widget.
    """
    widget = models.ForeignKey(Widget)
    job = models.ForeignKey(Job)

    def __unicode__(self):
        return "<WidgetJob %s: widget %s, job %s>" % (self.id,
                                                      self.widget.id,
                                                      self.job.id)

    def save(self, *args, **kwargs):
        with transaction.commit_on_success():
            self.job.reference(str(self))
            super(WidgetJob, self).save(*args, **kwargs)


@receiver(pre_delete, sender=WidgetJob)
def _widgetjob_delete(sender, instance, **kwargs):
    try:
        instance.job.dereference(str(instance))
    except ObjectDoesNotExist:
        logger.info('Job not found for instance %s, ignoring.' % instance)


class Axes:
    def __init__(self, definition):
        self.definition = definition

    def getaxis(self, colname):
        if self.definition is not None:
            for n, v in self.definition.items():
                if ('columns' in v) and (colname in v['columns']):
                    return int(n)
        return 0

    def position(self, axis):
        axis = str(axis)
        if ((self.definition is not None) and
            (axis in self.definition) and ('position' in self.definition[axis])):
            return self.definition[axis]['position']
        return 'left'
