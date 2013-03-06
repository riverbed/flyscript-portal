from report.models import *
import rvbd.profiler
from rvbd.profiler.filters import TimeFilter

# Used by DeviceManger to create a Profiler instance
def DeviceManager_new(*args, **kwargs):
    return rvbd.profiler.Profiler(*args, **kwargs)

# Used by DataTable to actually run a query
class DataTable_Query:
    def __init__(self, datatable, job):
        self.datatable = datatable
        self.job = job
        
    def run(self):
        cachefile = "datatable-%s.cache" % self.datatable.id
        if os.path.exists(cachefile):
            # XXXCJ This cachefile hack is temporary and is only good for testing to avoid actually
            # having to run the report every single time.
            logger.debug("Using cache file")
            f = open(cachefile, "r")
            self.data = pickle.load(f)
            f.close()
        else:
            logger.debug("Running new report")
            datatable = self.datatable

            profiler = DeviceManager.get_device(datatable.options['device'])
            report = rvbd.profiler.report.SingleQueryReport(profiler)

            columns = []

            for dc in datatable.datacolumn_set.all():
                columns.append(dc.querycol)
                
            sortcol=None
            if datatable.sortcol is not None:
                sortcol=datatable.sortcol.querycol

            if 'realm' in datatable.options:
                realm = datatable.options['realm']
            else:
                realm = 'traffic_summary'

            with lock:
                report.run( realm=realm,
                            groupby = profiler.groupbys[datatable.options['groupby']],
                            columns = columns,
                            timefilter = TimeFilter.parse_range("last %d m" % datatable.duration),
                            resolution="%dmin" % (int(datatable.resolution / 60)),
                            sort_col=sortcol,
                            sync=False
                            )

            done = False
            logger.info("Waiting for report to complete")
            while not done:
                sleep(0.5)
                with lock:
                    s = report.status()

                self.job.progress = int(s['percent'])
                self.job.save()
                done = (s['status'] == 'completed')

            # Retrieve the data
            with lock:
                self.data = report.get_data()

            if datatable.rows > 0:
                self.data = self.data[:datatable.rows]
                
            f = open(cachefile, "w")
            pickle.dump(self.data, f)
            f.close()

        return True
