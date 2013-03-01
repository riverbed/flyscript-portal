# Create your views here.
import os
import json
import random
import threading
import datetime
import pickle
from time import sleep

from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext, loader
from django.conf import settings

from rvbd.common import UserAuth

from report.models import *

import logging
logger = logging.getLogger('report')

def root(request):
    try:
        reports = Report.objects.all()
    except:
        return HttpResponse("No reports defined!")

    return HttpResponseRedirect('/report/%d' % reports[0].id)

def main(request, report_id):
    try:
        report = Report.objects.get(pk=int(report_id))
    except:
        raise Http404

    reports = Report.objects.all()
    
    t = loader.get_template('report.tpl')

    lastrow = -1
    i = -1
    rows = []
    for w in Widget.objects.filter(report=report).order_by('row','col'):
        if w.row != lastrow:
            i = i+1
            lastrow = w.row
            rows.append([])
        rows[i].append(Widget.objects.get_subclass(id=w.id))

    c = RequestContext( request,
                        { 'report' : report,
                          'reports' : reports,
                          'rows': rows} )
    
    return HttpResponse(t.render(c))

