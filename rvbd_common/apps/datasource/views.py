# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import json
import logging

from rest_framework.reverse import reverse
from rest_framework import generics

from rvbd_common.apps.datasource.serializers import (TableSerializer,
                                         ColumnSerializer,
                                         JobSerializer,
                                         JobDataSerializer,
                                         JobListSerializer)
from rvbd_common.apps.datasource.models import Table, Column, Job, Criteria


logger = logging.getLogger(__name__)


class TableList(generics.ListCreateAPIView):
    model = Table
    serializer_class = TableSerializer
    paginate_by = 20


class TableDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Table
    serializer_class = TableSerializer


class TableColumnList(generics.ListCreateAPIView):
    model = Column
    serializer_class = ColumnSerializer
    paginate_by = 20

    def get_queryset(self):
        """Filter results to specific table."""
        return Column.objects.filter(table=self.kwargs['pk'])


class TableJobList(generics.ListCreateAPIView):
    model = Job
    serializer_class = JobSerializer

    def get_queryset(self):
        """Filter results to specific table."""
        return Job.objects.filter(table=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        # auto-populate table info for criteria values
        data = request.DATA.copy()
        data['table'] = self.kwargs['pk']
        request._data = data
        return super(TableJobList, self).post(request, *args, **kwargs)

    def pre_save(self, obj):
        """Populate criteria object with defaults."""
        try:
            criteria = Criteria(table=obj.table,
                                **json.loads(self.request.POST['criteria']))
        except KeyError:
            criteria = Criteria(table=obj.table)

        obj.criteria = criteria

    def post_save(self, obj, created=False):
        # kickoff job once its been created
        if created:
            obj.start()

    def get_success_headers(self, data):
        # override method to return location of new job resource
        try:
            job = self.object
            url = reverse('job-detail', args=(job.pk,), request=self.request)
            return {'Location': url}
        except (TypeError, KeyError):
            return {}


class ColumnList(generics.ListCreateAPIView):
    model = Column
    serializer_class = ColumnSerializer
    paginate_by = 20


class ColumnDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Column
    serializer_class = ColumnSerializer


class JobList(generics.ListCreateAPIView):
    model = Job
    serializer_class = JobListSerializer
    paginate_by = 10

    def post_save(self, obj, created=False):
        if created:
            obj.start()

    def get_success_headers(self, data):
        # override method to return location of new job resource
        try:
            job = self.object
            url = reverse('job-detail', args=(job.pk,), request=self.request)
            return {'Location': url}
        except (TypeError, KeyError):
            return {}


class JobDetail(generics.RetrieveAPIView):
    model = Job
    serializer_class = JobSerializer


class JobDetailData(generics.RetrieveAPIView):
    model = Job
    serializer_class = JobDataSerializer

