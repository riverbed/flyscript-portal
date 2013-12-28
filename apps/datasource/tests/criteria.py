# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import datetime
import pytz
import dateutil.parser

from django.test import TestCase
from apps.datasource.models import Table, Column
from apps.datasource.forms import TableFieldForm
from apps.datasource.modules.analysis import AnalysisTable
from apps.report.models import Report
from apps.datasource.forms import fields_add_time_selection

from rvbd.common import datetime_to_seconds

from . import criteria_helpers

class Criteria(TestCase):
    def test_default_endtime(self):
        report = Report(title="Test Criteria", position=0)
        report.save()
        
        fields_add_time_selection(report, initial_duration="1 day")

        data = {'endtime': '12/21/2013 9:00 am'}
        form = TableFieldForm(report.criteria.all(), use_widgets=False, data=data)
        
        self.assertTrue(form.is_valid(), "form.errors: %s" % form.errors)

        criteria = form.criteria()
        criteria.compute_times()

        self.assertEqual(criteria.starttime, dateutil.parser.parse('12/20/2013 9:00 am'))
        self.assertEqual(criteria.duration, datetime.timedelta(1))

        #t = AnalysisTable.create('test-criteria', tables={},
        #                          func = criteria_helpers.criteria)

        #Column.create(t, 'key', 'Key', iskey=True, isnumeric=False)
        #Column.create(t, 'value', 'Value', isnumeric=False)

        
