# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import datetime
import logging
import tempfile

import dateutil.parser

from django.test import Client

from rvbd_portal.apps.datasource.models import Job
from rvbd_portal.apps.report.models import Report, Widget, Section
from . import reportrunner
from rvbd_portal.libs.call_command import call_command


logger = logging.getLogger(__name__)

class CriteriaTest(reportrunner.ReportRunnerTestCase):

    def run_with_criteria(self, criteria, expected=None, report=None,
                          expect_fail_report=False, expect_fail_job=False):
        self.run_report_with_criteria(criteria, report=report, expected=expected,
                                      expect_fail_report=expect_fail_report,
                                      expect_fail_job=expect_fail_job)
        if not expect_fail_report and not expect_fail_job:
            self.run_tables_with_criteria(criteria, expected=expected)

    def run_report_with_criteria(self, criteria, expected=None, report=None,
                                 expect_fail_report=False, expect_fail_job=False):
        """ Run the report via views, much like the UI. """
        if report is None:
            report = self.report

        # If not provided, expected result should match input criteria
        if expected is None:
            expected = [criteria]
        elif not isinstance(expected, list):
            expected = [expected]

        # Perform a little magic on endtime because the way report
        # processing works, the endtime is actuall split into two pieces
        # by the django forms processor
        run_criteria = {}
        for k,v in criteria.iteritems():
            if k == 'endtime':
                (e0, e1) = v.split(' ',1)
                run_criteria['endtime_0'] = e0
                run_criteria['endtime_1'] = e1
            else:
                run_criteria[k] = v

        # Now, run the report and get back all the widget data indexed
        # by job url
        widgets = self.run_report(run_criteria, report,
                                  expect_fail_report=expect_fail_report,
                                  expect_fail_job=expect_fail_job)

        if expect_fail_report or expect_fail_job:
            return

        # Verify the results
        for i,e in enumerate(expected):
            w = widgets.values()[i]
            self.assertEqual(w['status'], Job.COMPLETE,
                             'Widget %d, message %s' % (i, w['message']))

            returned_criteria = dict(w['data'])
            logger.debug("Widget %d, returned_criteria: %s" % (i, returned_criteria))

            for k,v in e.iteritems():
                self.assertEqual(returned_criteria[k], v,
                                 "Key %s => %s vs %s" %
                                 (k, v, returned_criteria[k]))

    def run_tables_with_criteria(self, criteria, expected=None, report=None,
                                 expect_fail_report=False, expect_fail_job=False):
        """ Run the tables via the command line run_table command. """
        if report is None:
            report = self.report

        if expected is None:
            expected = [criteria]
        elif not isinstance(expected, list):
            expected = [expected]

        report = Report.objects.get(slug = report)
        tables = []
        for w in Widget.objects.filter(section__in = report.section_set.all()):
            tables.extend(w.tables.all())

        for i,t in enumerate(tables):

            with tempfile.NamedTemporaryFile() as outfile:
                filename = outfile.name

            r = call_command('run_table',
                             table_id=t.id,
                             as_csv=True,
                             output_file=filename,
                             criteria=['%s:%s' % (k,v) for (k,v) in criteria.iteritems()])

            data = []
            with open(filename, 'r') as f:
                for line in f:
                    data.append(line.strip().split(',',1))

            returned_criteria = {}
            for k,v in data[1:]:
                returned_criteria[k] = v

            logger.debug("Table %s, returned_criteria: %s" % (t.id, returned_criteria))

            for k,v in expected[i].iteritems():
                self.assertEqual(returned_criteria[k], v,
                                 "Key %s => %s vs %s" %
                                 (k, v, returned_criteria[k]))

class CriteriaTimeSelection(CriteriaTest):

    report = 'criteria_timeselection'

    def test_duration_1day(self):
        self.run_with_criteria({'endtime': '12/1/2013 11:00 am +0000',
                                'duration': '1 week'},
                               {'duration': str(datetime.timedelta(days=7)),
                                'starttime': str(dateutil.parser.parse("11/24/2013 11:00am +0000")),
                                'endtime': str(dateutil.parser.parse("12/1/2013 11:00am +0000"))})

    def test_duration_5min(self):
        self.run_with_criteria({'endtime': '12/1/2013 11:00 am +0000',
                                'duration': '5 min'},
                               {'duration': str(datetime.timedelta(seconds=60*5)),
                                'starttime': str(dateutil.parser.parse("12/1/2013 10:55am +0000")),
                                'endtime': str(dateutil.parser.parse("12/1/2013 11:00am +0000"))})

    def test_bad_time(self):
        self.run_with_criteria({'endtime': '12/1f/2013 11:00 am +0000',
                                'duration': '5 min'},
                               expect_fail_report=True)


class CriteriaPreProcess(CriteriaTest):

    report = 'criteria_preprocess'

    def test(self):
        self.run_with_criteria({'choices' : 'val1',
                                'choices_with_params' : 'pre_val1'})

        self.run_with_criteria({'choices' : 'val2',
                                'choices_with_params' : 'pre_val3'})



class CriteriaPostProcess(CriteriaTest):

    report = 'criteria_postprocess'

    def test(self):
        self.run_with_criteria({'w' : '1', 'x' : '2', 'y': '5'},
                               {'wx' : '3', 'wy' : '6', 'xy': '7'})

class CriteriaSharedFields(CriteriaTest):

    report = 'criteria_sharedfields'

    def test(self):
        self.run_with_criteria({'x': '1'},
                               [ {'x': '1', 'y': '12'},
                                 {'x': '1', 'y': '22'} ])

class CriteriaPostProcessErrors(CriteriaTest):

    report = 'criteria_postprocesserrors'

    def test_no_error(self):
        self.run_with_criteria({'error': 'none'},
                               {'x' : '1'})

    def test_syntax(self):
        self.run_with_criteria({'error': 'syntax'},
                               expect_fail_job=True)


class CriteriaParents(CriteriaTest):

    report = 'criteria_parents'

    def test(self):
        self.run_with_criteria({'report_independent': 'top'},

                               {'report_independent': 'top',
                                'report_computed' : 'report_computed:top',
                                'section_computed' : 'section_computed:report_computed:top',
                                'table_computed' : 'table_computed:section_computed:report_computed:top'})

class CriteriaDefaults(CriteriaTest):

    report = 'criteria_defaults'

    def test(self):
        self.run_with_criteria({}, {}, expect_fail_report=True)

        self.run_with_criteria({'report-2': 'r22'},

                               {'report-1': 'r1',
                                'report-2': 'r22',
                                'section-1': 's1',
                                'section-2': 's2',
                                'table-1': 't1',
                                'table-2': 't2'})

        self.run_with_criteria({'report-1': 'r11',
                                'report-2': 'r22'},

                               {'report-1': 'r11',
                                'report-2': 'r22',
                                'section-1': 's1',
                                'section-2': 's2',
                                'table-1': 't1',
                                'table-2': 't2'})

        self.run_with_criteria({'report-1': 'r11',
                                'report-2': 'r22',
                                'table-1': 't11'},

                               {'report-1': 'r11',
                                'report-2': 'r22',
                                'section-1': 's1',
                                'section-2': 's2',
                                'table-1': 't11',
                                'table-2': 't2'})


class CriteriaSectionKeywords(CriteriaTest):

    report = 'criteria_sectionkeywords'

    def test(self):
        report = Report.objects.get(slug__endswith=self.report)
        section0 = Section.objects.get(report=report, title="Section 0")
        section1 = Section.objects.get(report=report, title="Section 1")
        self.run_report_with_criteria({'__s%s_k1' % section0.id: 'v1',
                                       '__s%s_k1' % section1.id: 'v2'},

                                      [{'k1' : 'v1'},
                                       {'k1' : 'v2'}])


class CriteriaChangingChoices(CriteriaTest):

    report = 'criteria_changingchoices'

    def test(self):
        self.run_with_criteria({'first' : 'a',
                                'second' : 'a-1'})

        self.run_with_criteria({'first' : 'b',
                                'second' : 'b-2'})

        self.run_with_criteria({'first' : 'b',
                                'second' : 'a-1'},
                               expect_fail_report=True)

        self.run_with_criteria({'first' : 'a',
                                'second' : 'b-2'},
                               expect_fail_report=True)

class CriteriaChangingChoicesWithSections(CriteriaTest):

    report = 'criteria_changingchoiceswithsections'

    def test(self):
        report = Report.objects.get(slug__endswith=self.report)
        section0 = Section.objects.get(report=report, title="Section 0")
        section1 = Section.objects.get(report=report, title="Section 1")
        self.run_report_with_criteria({'__s%s_first' % section0.id: 'a',
                                       '__s%s_second' % section0.id : 'a-1',
                                       '__s%s_first' % section1.id: 'b',
                                       '__s%s_second' % section1.id : 'b-2'},

                                      [{'first' : 'a', 'second' : 'a-1'},
                                       {'first' : 'b', 'second' : 'b-2'} ])

class CriteriaCircularDependency(CriteriaTest):

    report = 'criteria_circulardependency'

    def test(self):
        self.run_report_with_criteria({}, expect_fail_report=True)

class CriteriaTwoReports(CriteriaTest):

    report = ['criteria_tworeports_1', 'criteria_tworeports_2']

    def test(self):
        self.run_report_with_criteria({'k1': '2'},
                                      {'k1': '2', 'k2': 'r2'},
                                      report=self.report[1])

        self.load_report(self.report[0])

        # Need to re-login
        self.client = Client()
        self.client.login(username='admin', password='admin')

        self.run_report_with_criteria({'k1': '2'},
                                      {'k1': '2', 'k2': 'r2'},
                                      report=self.report[1])
