import glob
import time
import os
import json
import logging

from django.test import TestCase, Client
from django.core import management
from django.utils.datastructures import SortedDict

from rvbd_portal.apps.datasource.models import Job
from rvbd_portal.apps.report.models import Report, Widget

logger = logging.getLogger(__name__)


class ReportRunnerTestCase(TestCase):

    report = None

    @classmethod
    def setUpClass(cls):
        localdir = os.path.dirname(__file__)
        initial_data = glob.glob(os.path.join(localdir, '*.json'))
        management.call_command('loaddata', *initial_data)

        if not isinstance(cls.report, list):
            reports = [cls.report]
        else:
            reports = cls.report

        for report in reports:
            cls.load_report(report)

    @classmethod
    def load_report(cls, report):
            path = 'rvbd_portal.apps.report.tests.reports.' + report
            logger.info("Loading report: %s" % path)
            management.call_command('reload', report_name=path)

    def setUp(self):
        logger.info('Logging in as admin')
        logger.info('Report count: %d' % len(Report.objects.all()))
        self.client = Client()
        self.assertTrue(self.client.login(username='admin', password='admin'))

    def check_status(self, response, expect_fail):
        sc = int(response.status_code)
        if (sc >= 400 and sc < 500):
            logger.info("Report error response code %s\n%s" %
                        (sc, response.content))
            self.assertTrue(expect_fail)
            return

        self.assertTrue(not expect_fail)
        self.assertEqual(response.status_code, 200)

    def run_report(self, criteria, report=None,
                   expect_fail_report=False, expect_fail_job=False):
        if report is None:
            report = self.report

        logger.info("Running report %s with criteria:\n%s" %
                    (report, criteria))

        try:
            response = self.client.post('/report/rvbd_portal/%s/' % report,
                                        data=criteria)
        except:
            self.assertTrue(expect_fail_report)
            return

        self.check_status(response, expect_fail_report)
        if expect_fail_report:
            return

        report_data = json.loads(response.content)
        logger.debug("Report data:\n%s" % json.dumps(report_data, indent=2))

        widgets = SortedDict()
        for widget_data in report_data[1:]:
            wid = widget_data['widgetid']
            widget = Widget.objects.get(id=wid)
            logger.info('Processing widget %s' % widget)

            # POST to the widget url to create the WidgetJob instance
            widget_url = widget_data['posturl']
            widget_criteria = widget_data['criteria']
            postdata = {'criteria': json.dumps(widget_criteria)}
            logger.debug("Widget post data:\n%s" % (json.dumps(postdata, indent=2)))
            response = self.client.post(widget_url, data=postdata)
            self.check_status(response, expect_fail_job)

            if expect_fail_job:
                return

            widgetjob_data = json.loads(response.content)
            logger.debug("Widget response data:\n%s" % (json.dumps(widgetjob_data, indent=2)))

            # Extract the job url and get the first response
            joburl = widgetjob_data['joburl']
            widgets[joburl] = None

        for joburl in widgets:
            while True:
                response = self.client.get(joburl)
                job_data = json.loads(response.content)
                widgets[joburl] = job_data
                logger.debug("Widget job data:\n%s" % (json.dumps(job_data, indent=2)))
                if widgets[joburl]['status'] not in [Job.COMPLETE, Job.ERROR]:
                    time.sleep(0.1)
                else:
                    break

        return widgets
