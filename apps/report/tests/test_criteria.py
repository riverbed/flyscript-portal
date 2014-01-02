# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import datetime
import dateutil.parser
import logging

from rvbd.common import datetime_to_seconds

from apps.datasource.forms import fields_add_time_selection
from apps.datasource.modules.analysis import AnalysisTable

import apps.report.modules.raw as raw

from . import reportrunner

logger = logging.getLogger(__name__)

class CriteriaTest(reportrunner.ReportRunnerTestCase):

    def run_with_criteria(self, criteria, expected=None):
        if expected is None:
            expected = criteria
            
        widgets = self.run_report(criteria)

        returned_criteria = dict(widgets.values()[0]['data'])

        for k,v in expected.iteritems():
            self.assertEqual(returned_criteria[k], v,
                             "Key %s => %s vs %s" %
                             (k, v, returned_criteria[k]))
    
class TimeSelection(CriteriaTest):

    report = 'criteria_timeselection' 

    def test_default(self):
        self.run_with_criteria({'endtime_0': '12/1/2013', 'endtime_1': '11:00 am',  
                                'duration': 'Default'},
                               {'duration': str(datetime.timedelta(seconds=60)),
                                'starttime': str(dateutil.parser.parse("12/1/2013 10:59am +0000")),
                                'endtime': str(dateutil.parser.parse("12/1/2013 11:00am +0000"))})
                                

    def test_duration_1day(self):
        self.run_with_criteria({'endtime_0': '12/1/2013', 'endtime_1': '11:00 am',  
                                'duration': '1 week'},
                               {'duration': str(datetime.timedelta(days=7)),
                                'starttime': str(dateutil.parser.parse("11/24/2013 11:00am +0000")),
                                'endtime': str(dateutil.parser.parse("12/1/2013 11:00am +0000"))})

    def test_duration_5min(self):
        self.run_with_criteria({'endtime_0': '12/1/2013', 'endtime_1': '11:00 am',  
                                'duration': '5 min'},
                               {'duration': str(datetime.timedelta(seconds=60*5)),
                                'starttime': str(dateutil.parser.parse("12/1/2013 10:55am +0000")),
                                'endtime': str(dateutil.parser.parse("12/1/2013 11:00am +0000"))})


class PreProcess(CriteriaTest):

    report = 'criteria_preprocess' 

    def test(self):
        self.run_with_criteria({'choices' : 'val1',
                                'choices_with_params' : 'pre_val1'})

        self.run_with_criteria({'choices' : 'val2',
                                'choices_with_params' : 'pre_val3'})



class PostProcess(CriteriaTest):

    report = 'criteria_postprocess' 

    def test(self):
        self.run_with_criteria({'w' : '1', 'x' : '2', 'y': '5'},
                               {'wx' : '3', 'wy' : '6', 'xy': '7'})



