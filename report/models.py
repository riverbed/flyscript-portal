from time import sleep
import math
import datetime
import shutil
import os
import pickle
import sys
import traceback
import threading
import json
from model_utils.managers import InheritanceManager
from misc.fields import PickledObjectField
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.exceptions import ObjectDoesNotExist
from misc.nicescale import NiceScale

from rvbd.common import UserAuth
from rvbd.common.connection import Connection
from rvbd.profiler import *
from rvbd.profiler.filters import TimeFilter, TrafficFilter

import logging
logger = logging.getLogger('report')

lock = threading.Lock()

Connection.DEBUG_MSG_BODY=1000

class DeviceManager:
    devices = {}

    @classmethod
    def get_device(cls, device_id):
        if device_id not in cls.devices:
            try:
                dbdevice = Device.objects.get(pk=device_id)
            except:
                raise ValueError("Could not find device by id: %d" % device_id)

            logger.debug("Creating new Profiler")
            cls.devices[device_id] = Profiler(dbdevice.host, port=dbdevice.port,
                                               auth=UserAuth(dbdevice.username,
                                                             dbdevice.password))
        return cls.devices[device_id]

class Device(models.Model):
    name = models.CharField(max_length=200)
    host = models.CharField(max_length=200)
    port = models.IntegerField()
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

class Report(models.Model):
    title = models.CharField(max_length=200)

    def __unicode__(self):
        return self.title

class Widget(models.Model):
    device = models.ForeignKey(Device)
    report = models.ForeignKey(Report)
    title = models.CharField(max_length=100)
    row = models.IntegerField()
    col = models.IntegerField()
    colwidth = models.IntegerField(default=1)
    rows = models.IntegerField(default=-1)
    
    objects = InheritanceManager()
    
    def __unicode__(self):
        return self.title

    def widgettype(self):
        return 'Widget'

    def data(self, request, job=None):
        return self.title

    def options(self):
        return {"minHeight": 300}
    
    def poll(self, request):
        ts = request.GET['ts']
        
        # Create a job handle based on report and widget id
        h = "job-w%s-t%s" % (self.id, str(ts))

        try:
            job = Job.objects.get(handle=h)
            logger.debug("Got job: %s" % job.data)

        except ObjectDoesNotExist:
            logger.debug("No Job for handle %s" % h)
            job = Job(handle=h)
            job.data = {'widget_id' : self.id,
                        'ts' : ts }
            job.save()
            self.startjob(job)

        resp = WidgetResponse(job.progress, job.remaining, job.status)
        
        if not job.done():
            # job not yet done, return an empty data structure
            logger.debug("widget.data: Not done yet, %d%% complete" % job.progress)
        else:
            resp.data = self.data(request, job)
            logger.debug("widget.data: Responding with full data")
            job.delete()
        
        return resp.httpresponse()
    
    def startjob(self, job):
        j = AsyncWorker(job.handle)
        j.start()

class WidgetColumn(models.Model):
    widget = models.ForeignKey(Widget)

    querycol = models.CharField(max_length=30)
    label = models.CharField(max_length=30)
    formatter = models.CharField(max_length=50, default='')
    
    objects = InheritanceManager()

    axis = models.IntegerField(default=0)

    def __unicode__(self):
        return self.label

class WidgetResponse:
    def __init__(self, progress=-1, remaining=-1, status=0, message=None, data=None):
        self.progress = progress
        self.remaining = remaining
        self.status = status
        self.message = message
        self.data = data
        
    def httpresponse(self):
        j = { 'progress': self.progress,
              'remaining': self.remaining,
              'status': self.status,
              'message': self.message,
              'data': self.data }
        return HttpResponse(json.dumps(j))
    
def widgetdata(request, report_id, widget_id):
    try:
        widget = Widget.objects.get_subclass(id=int(widget_id))
        return widget.poll(request)
    except ObjectDoesNotExist:
        return WidgetResponse(status=Job.ERROR, message="Failed to find Widget %s" % widget_id).httpresponse()
    except:
        traceback.print_exc()
        logger.error("widgetdata poll: %s" % (str(sys.exc_info())))
        return WidgetResponse(status=Job.ERROR, message="Internal Error").httpresponse()

#
# Job
#
class Job(models.Model):
    handle = models.CharField(max_length=100)

    NEW = 0
    RUNNING = 1
    COMPLETE = 2
    ERROR = 3
    
    status = models.IntegerField(default=NEW,
                                 choices = ((NEW, "New"),
                                            (RUNNING, "Running"),
                                            (COMPLETE, "Complete"),
                                            (ERROR, "Error")))
    message = models.CharField(max_length=200, default="")
    progress = models.IntegerField(default=-1)
    remaining = models.IntegerField(default=-1)

    data = PickledObjectField()
    
    def __unicode__(self):
        return "%s, %s %s%%" % (self.handle, self.status, self.progress)
    

    def done(self):
        return self.status == Job.COMPLETE or self.status == Job.ERROR
    
class AsyncWorker(threading.Thread):
    def __init__(self, handle):
        threading.Thread.__init__(self)
        self.handle = handle
        
    def work(self):
        pass
    
    def run(self):
        logger.debug("Starting job %s" % self.handle)
        job = Job.objects.get(handle=self.handle)
        try:
            self.work()
            logger.debug("Saving job %s as COMPLETE" % self.handle)
            job.progress = 100
            job.status=job.COMPLETE
        except :
            logger.error("Job %s failed: %s" % (self.handle, str(sys.exc_info())))
            job.status = job.ERROR
            job.progress = 100
            job.message = sys.exc_info()[0]

        job.save()
        sys.exit(0)

class ProfilerReport(AsyncWorker):
    def __init__(self, handle, datafile, widget_id):
        AsyncWorker.__init__(self, handle)
        self.datafile = datafile
        self.widget_id = widget_id

    def create(self, device):
        pass
    
    def runreport(self, report, widget):
        pass
    
    def work(self):
        datafile = self.datafile
        widget = Widget.objects.get_subclass(id=self.widget_id)
        cachefile = datafile + ".cache"

        print "Looking for cachefile: %s" % cachefile
        if os.path.exists(cachefile):
            logger.info("Using cache file")
            shutil.copy2(cachefile, datafile)
        else:
            logger.info("Creating new report")
            device = DeviceManager.get_device(widget.device_id)

            report = self.create(device)
            
            lock.acquire(True);
            self.runreport(report, widget)
            lock.release()

            done = False
            logger.info("Waiting for report to complete")
            while not done:
                sleep(0.5)
                lock.acquire(True)
                s = report.status()
                lock.release()
                if s['status'] == 'completed':
                    done = True

            # Retrieve and print data
            lock.acquire(True)
            reportdata = report.get_data()
            lock.release()

            if widget.rows > 0:
                reportdata = reportdata[:widget.rows]
                
            f = open(cachefile, "w")
            pickle.dump(reportdata, f)
            f.close()
            shutil.copy2(cachefile, datafile)


#
# TimeSeriesWidget
#
class TimeSeriesWidget(Widget):
    traffic_expr = models.TextField(blank=True)
    duration = models.IntegerField() # length of graph in minutes
    resolution = models.IntegerField(default=60) # resolution of graph in seconds
    stacked = models.BooleanField(default=False)

    def widgettype(self):
        return 'TimeSeriesWidget'

    def startjob(self, job):
        datafile = "widget_data_%s_%s" % (self.report.id, self.id)
        logger.warn("TimeSeriesWidget.startReport")
        report = TimeSeriesWidgetReport(job.handle, datafile, self.id)
        report.start()
        
    def data(self, request, job=None):
        did = self.report.id
        wid = self.id
        
        datafile = "widget_data_%s_%s" % (did, wid)

        f = open(datafile, "r")
        reportdata = pickle.load(f)
        f.close()

        series = []
        qcols = ["time"]
        qcol_axis = [ -1]
        axes = { "time" : { "keys" : ["time"],
                            "position": "bottom",
                            "type": "time",
                            "labelFormat": "%l:%M %p",
                            "styles" : { "label": { "rotation": -60 }}}}

        for wc in self.widgetcolumn_set.all():
            series.append({"xKey": "time",
                           "yKey": wc.querycol,
                           "styles": { "line": { "weight" : 1 },
                                       "marker": { "height": 6,
                                                   "width": 6 }}})
            qcols.append(wc.querycol)
            qcol_axis.append(wc.axis)
            axis_name = 'axis'+str(wc.axis)
            if axis_name not in axes:
                axes[axis_name] = {"type": "numeric",
                                   "position" : "left" if (wc.axis == 0) else "right",
                                   "keys": []
                                   }

            axes[axis_name]['keys'].append(wc.querycol)
            
        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        for reportrow in reportdata:
            row = {'time': reportrow[0] * 1000}
            rowmin = {}
            rowmax = {}
            for i in range(1,len(qcols)):
                a = qcol_axis[i]
                val = reportrow[i]
                row[qcols[i]] = val
                if a not in rowmin:
                    rowmin[a] = val
                    rowmax[a] = val
                else:
                    rowmin[a] = (rowmin[a] + val) if self.stacked else min(rowmin[a], val)
                    rowmax[a] = (rowmax[a] + val) if self.stacked else max(rowmax[a], val)
                    
                i = i + 1

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a], rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a], rowmax[a])


            rows.append(row)

        for wc in self.widgetcolumn_set.all():
            axis_name = 'axis'+str(wc.axis)
            n = NiceScale(minval[wc.axis], maxval[wc.axis])

            axes[axis_name]['minimum'] = "%.10f" % n.niceMin
            axes[axis_name]['maximum'] = "%.10f" % n.niceMax
            axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
            axes[axis_name]['styles'] = { 'majorUnit' : {'count' : n.numTicks } }
            if wc.formatter != "":
                axes[axis_name]['formatter'] = wc.formatter
        data = {
            "chartTitle": self.title,
            "type" : "combo" if self.stacked else "combo",
            "stacked" : self.stacked,
            "dataProvider": rows,
            "seriesCollection" : series,
            "axes": axes
            }

        return data
        
    def __unicode__(self):
        return self.title

class TimeSeriesWidgetAxis(models.Model):
    widget = models.ForeignKey(TimeSeriesWidget)

    axis = models.IntegerField()
    label = models.CharField(max_length=100)
    
    def __unicode__(self):
        return "[%d] %s" % (self.axis, self.label)

class TimeSeriesWidgetReport(ProfilerReport):
        
    def create(self, device):
        return TrafficOverallTimeSeriesReport(device)
    
    def runreport(self, report, widget):
        columns = ["time"]

        for wc in widget.widgetcolumn_set.all():
            columns.append(wc.querycol)
            
        report.run( columns = columns,
                    timefilter = TimeFilter.parse_range("last %d m" % widget.duration),
                    resolution="%dmin" % (int(widget.resolution / 60)),
                    sync=False
                    )

#
# TableWidget
#
class TableWidget(Widget):
    traffic_expr = models.TextField(blank=True)
    duration = models.IntegerField() # length of graph in minutes
    resolution = models.IntegerField(default=60) # resolution of graph in seconds
    groupby = models.CharField(max_length=50)
    sortcol = models.ForeignKey(WidgetColumn, null=True)
    sortable = models.BooleanField(default=False)
    
    def widgettype(self):
        return 'TableWidget'

    def startjob(self, job):
        datafile = "widget_data_%s_%s" % (self.report.id, self.id)
        logger.warn("TableWidget.startReport")
        report = TableWidgetReport(job.handle, datafile, self.id)
        report.start()
        
    def data(self, request, job=None):
        did = self.report.id
        wid = self.id
        
        datafile = "widget_data_%s_%s" % (did, wid)

        f = open(datafile, "r")
        reportdata = pickle.load(f)
        f.close()

        qcols = []
        columns = []
        
        for wc in self.widgetcolumn_set.all():
            qcols.append(wc.querycol)
            column = {'key': wc.querycol, 'label': wc.label, "sortable": True}
            if wc.formatter != "":
                column['formatter'] = wc.formatter
            columns.append(column)
            
        rows = []

        for reportrow in reportdata:
            row = {}
            for i in range(0,len(qcols)):
                val = reportrow[i]
                row[qcols[i]] = val
                i = i + 1

            rows.append(row)

        data = {
            "chartTitle": self.title,
            "columns" : columns,
            "data": rows
            }

        return data
        
    def __unicode__(self):
        return self.title

class TableWidgetReport(ProfilerReport):
        
    def create(self, device):
        return TrafficSummaryReport(device)

    def runreport(self, report, widget):
        columns = []
        
        for wc in widget.widgetcolumn_set.all():
            columns.append(wc.querycol)
            
        sortcol=None
        if widget.sortcol is not None:
            sortcol=widget.sortcol.querycol
                
        report.run( groupby = widget.groupby,
                    columns = columns,
                    timefilter = TimeFilter.parse_range("last %d m" % widget.duration),
                    resolution="%dmin" % (int(widget.resolution / 60)),
                    sort_col=sortcol,
                    sync=False
                    )

#
# ColumnWidget
#
class ColumnWidget(Widget):
    traffic_expr = models.TextField(blank=True)
    duration = models.IntegerField() # length of graph in minutes
    resolution = models.IntegerField(default=60) # resolution of graph in seconds
    groupby = models.CharField(max_length=50)
    sortcol = models.ForeignKey(WidgetColumn, null=True)
    sortable = models.BooleanField(default=False)
    
    def widgettype(self):
        return 'ColumnWidget'

    def startjob(self, job):
        datafile = "widget_data_%s_%s" % (self.report.id, self.id)
        logger.warn("ColumnWidget.startReport")
        report = ColumnWidgetReport(job.handle, datafile, self.id)
        report.start()
        
    def data(self, request, job=None):
        did = self.report.id
        wid = self.id
        
        datafile = "widget_data_%s_%s" % (did, wid)

        f = open(datafile, "r")
        reportdata = pickle.load(f)
        f.close()

        widgetcols = self.widgetcolumn_set.all()
        catcol = widgetcols[0]
        datacols = widgetcols[1:]
        
        series = []
        qcols = [catcol.querycol]
        qcol_axis = [ -1]
        axes = { catcol.querycol : { "keys" : [catcol.querycol],
                                     "position": "bottom",
                                     "styles" : { "label": { "rotation": -60 }}}}

        for wc in datacols:
            series.append({"xKey": catcol.querycol,
                           "yKey": wc.querycol,
                           "styles": { "line": { "weight" : 1 },
                                       "marker": { "height": 6,
                                                   "width": 20 }}})
            qcols.append(wc.querycol)
            qcol_axis.append(wc.axis)
            axis_name = 'axis'+str(wc.axis)
            if axis_name not in axes:
                axes[axis_name] = {"type": "numeric",
                                   "position" : "left" if (wc.axis == 0) else "right",
                                   "keys": [] }

            axes[axis_name]['keys'].append(wc.querycol)
            
        rows = []

        # min/max values by axis 0/1
        minval = {}
        maxval = {}

        for reportrow in reportdata:
            row = {}
            rowmin = {}
            rowmax = {}
            for i in range(0,len(qcols)):
                a = qcol_axis[i]
                val = reportrow[i]
                row[qcols[i]] = val
                if a not in rowmin:
                    rowmin[a] = val
                    rowmax[a] = val
                else:
                    rowmin[a] = (rowmin[a] + val) if self.stacked else min(rowmin[a], val)
                    rowmax[a] = (rowmax[a] + val) if self.stacked else max(rowmax[a], val)
                    
                i = i + 1

            for a in rowmin.keys():
                minval[a] = rowmin[a] if (a not in minval) else min(minval[a], rowmin[a])
                maxval[a] = rowmax[a] if (a not in maxval) else max(maxval[a], rowmax[a])

            rows.append(row)

        for wc in datacols:
            axis_name = 'axis'+str(wc.axis)
            n = NiceScale(minval[wc.axis], maxval[wc.axis])

            axes[axis_name]['minimum'] = "%.10f" % n.niceMin
            axes[axis_name]['maximum'] = "%.10f" % n.niceMax
            axes[axis_name]['tickExponent'] = math.log10(n.tickSpacing)
            axes[axis_name]['styles'] = { 'majorUnit' : {'count' : n.numTicks } }

        data = {
            "chartTitle": self.title,
            "type" : "column",
            "categoryKey": catcol.querycol,
            "dataProvider": rows,
            "seriesCollection" : series,
            "axes": axes
            }

        return data
        
    def __unicode__(self):
        return self.title

class ColumnWidgetReport(ProfilerReport):
        
    def create(self, device):
        return TrafficSummaryReport(device)

    def runreport(self, report, widget):
        columns = []
        
        for wc in widget.widgetcolumn_set.all():
            columns.append(wc.querycol)
            
        sortcol=None
        if widget.sortcol is not None:
            sortcol=widget.sortcol.querycol
                
        report.run( groupby = widget.groupby,
                    columns = columns,
                    timefilter = TimeFilter.parse_range("last %d m" % widget.duration),
                    resolution="%dmin" % (int(widget.resolution / 60)),
                    sort_col=sortcol,
                    sync=False
                    )

#
# PieWidget
#
class PieWidget(Widget):
    traffic_expr = models.TextField(blank=True)
    duration = models.IntegerField() # length of graph in minutes
    resolution = models.IntegerField(default=60) # resolution of graph in seconds
    groupby = models.CharField(max_length=50)
    sortcol = models.ForeignKey(WidgetColumn, null=True)
    sortable = models.BooleanField(default=False)
    
    def widgettype(self):
        return 'PieWidget'

    def startjob(self, job):
        datafile = "widget_data_%s_%s" % (self.report.id, self.id)
        logger.warn("PieWidget.startReport")
        report = PieWidgetReport(job.handle, datafile, self.id)
        report.start()
        
    def data(self, request, job=None):
        did = self.report.id
        wid = self.id
        
        datafile = "widget_data_%s_%s" % (did, wid)

        f = open(datafile, "r")
        reportdata = pickle.load(f)
        f.close()

        widgetcols = self.widgetcolumn_set.all()
        catcol = widgetcols[0]
        datacols = widgetcols[1:]
        
        series = []
        qcols = [catcol.querycol]

        for wc in datacols:
            series.append({"categoryKey": catcol.querycol,
                           "valueKey": wc.querycol})
            qcols.append(wc.querycol)
            
        rows = []

        for reportrow in reportdata:
            row = {}
            for i in range(0,len(qcols)):
                val = reportrow[i]
                row[qcols[i]] = val
                i = i + 1

            rows.append(row)

        data = {
            "chartTitle": self.title,
            "type" : "pie",
            "categoryKey": catcol.querycol,
            "dataProvider": rows,
            "seriesCollection" : series,
            "legend" : { "position" : "right" }
            }

        return data
        
    def __unicode__(self):
        return self.title

class PieWidgetReport(ProfilerReport):
        
    def create(self, device):
        return TrafficSummaryReport(device)

    def runreport(self, report, widget):
        columns = []
        
        for wc in widget.widgetcolumn_set.all():
            columns.append(wc.querycol)
            
        sortcol=None
        if widget.sortcol is not None:
            sortcol=widget.sortcol.querycol
                
        report.run( groupby = widget.groupby,
                    columns = columns,
                    timefilter = TimeFilter.parse_range("last %d m" % widget.duration),
                    resolution="%dmin" % (int(widget.resolution / 60)),
                    sort_col=sortcol,
                    sync=False
                    )

