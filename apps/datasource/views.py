# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


# Create your views here.
import json
import datetime

from django.http import HttpResponse
from rest_framework import generics

from apps.datasource.serializers import \
     TableSerializer, ColumnSerializer, \
     JobSerializer, JobListSerializer
from apps.datasource.models import Table, Column, Job


import logging
logger = logging.getLogger(__name__)

class TableList(generics.ListCreateAPIView):
    model = Table
    serializer_class = TableSerializer
    
class TableDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Table
    serializer_class = TableSerializer
    
class ColumnList(generics.ListCreateAPIView):
    model = Column
    serializer_class = ColumnSerializer
        
class ColumnDetail(generics.RetrieveUpdateDestroyAPIView):
    model = Column
    serializer_class = ColumnSerializer
    
class JobList(generics.ListCreateAPIView):
    model = Job
    serializer_class = JobListSerializer

    def post_save(self, obj, created=False):
        obj.start()
    
class JobDetail(generics.RetrieveAPIView):
    model = Job
    serializer_class = JobSerializer

