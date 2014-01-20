import pandas
import logging
import datetime
import re
import copy
import pytz

from django.core.exceptions import ObjectDoesNotExist
from django import forms

from rvbd.common.timeutils import datetime_to_seconds, timedelta_total_seconds

from rvbd_common.apps.datasource.models import Job, Table, Column, TableField, BatchJobRunner
from rvbd_common.apps.datasource.modules.analysis import AnalysisTable, AnalysisException
from rvbd_common.apps.datasource.forms import fields_add_time_selection


logger = logging.getLogger(__name__)


def fields_add_business_hour_fields(report,
                                    default_start='8:00am',
                                    default_end='5:00pm',
                                    default_timezone='US/Eastern',
                                    default_weekends=False):

    fields_add_time_selection(report, initial_duration="1 week")

    TIMES = ['%d:00am' % h for h in range(1, 13)]
    TIMES.extend(['%d:00pm' % h for h in range(1, 13)])

    business_hours_start = TableField(keyword='business_hours_start',
                                      label='Start Business', initial=default_start,
                                      field_cls=forms.ChoiceField,
                                      field_kwargs={'choices': zip(TIMES, TIMES)},
                                      required=True)
    business_hours_start.save()
    report.fields.add(business_hours_start)

    business_hours_end = TableField(keyword='business_hours_end',
                                    label='End Business', initial=default_end,
                                    field_cls=forms.ChoiceField,
                                    field_kwargs={'choices': zip(TIMES, TIMES)},
                                    required=True)
    business_hours_end.save()
    report.fields.add(business_hours_end)

    business_hours_tzname = TableField(keyword='business_hours_tzname',
                                       label='Business Timezone', initial=default_timezone,
                                       field_cls=forms.ChoiceField,
                                       field_kwargs={'choices': zip(pytz.common_timezones,
                                                                    pytz.common_timezones)},
                                       required=True)
    business_hours_tzname.save()
    report.fields.add(business_hours_tzname)

    business_hours_weekends = TableField(keyword='business_hours_weekends',
                                         field_cls=forms.BooleanField,
                                         label='Business includes weekends',
                                         initial=default_weekends,
                                         required=False)
    business_hours_weekends.save()
    report.fields.add(business_hours_weekends)


def timestable():
    name = 'business_hours.timestable'
    try:
        table = Table.objects.get(name=name)
    except ObjectDoesNotExist:
        table = AnalysisTable.create(name, tables={}, func=compute_times)
        Column.create(table, 'starttime', 'Start time', datatype='time', iskey=True, issortcol=True)
        Column.create(table, 'endtime',   'End time', datatype='time', iskey=True)
        Column.create(table, 'totalsecs', 'Total secs')
    return table


def create(name, basetable, aggregate, other_tables=None, **kwargs):
    table = AnalysisTable.create(name, tables={'times': timestable().id},
                                 func=report_business_hours,
                                 params={'table': basetable.id,
                                         'aggregate': aggregate},
                                 **kwargs)

    table.copy_columns(basetable)
    [table.fields.add(f) for f in basetable.fields.all()]

    return table


def parse_time(t_str):
    m = re.match("^([0-9]+):([0-9][0-9]) *([aApP][mM]?)?$", t_str)
    if not m:
        raise ValueError("Could not parse time string: %s" % t_str)
    hours = int(m.group(1))
    minutes = int(m.group(2))
    ampm = m.group(3)
    if ampm:
        if ampm.lower()[0] == 'p':
            hours = hours + 12
    return datetime.time(hours, minutes, 0)


def replace_time(dt, t):
    return dt.replace(hour=t.hour,
                      minute=t.minute,
                      second=0,
                      microsecond=0)


def compute_times(target, tables, criteria, params):
    tzname = criteria.business_hours_tzname
    logger.debug("timezone: %s" % tzname)
    tz = pytz.timezone(tzname)

    # Convert to datetime objects in the requested timezone
    st = criteria.starttime.astimezone(tz)
    et = criteria.endtime.astimezone(tz)
    logger.debug("times: %s - %s" % (st, et))

    # Business hours start/end, as string "HH:MMam" like 8:00am
    sb = parse_time(criteria.business_hours_start)
    eb = parse_time(criteria.business_hours_end)

    weekends = criteria.business_hours_weekends

    # Iterate from st to et until
    times = []
    t = st
    while t <= et:
        # Set t0/t1 to date of t but time of sb/eb
        t0_t = replace_time(t, sb)
        t1_t = replace_time(t, eb)

        # Advance t by 1 day
        t = t + datetime.timedelta(days=1)

        # Skip weekends
        if not weekends and t0_t.weekday() >= 5:
            continue

        # Now see if we have any overlap of busines hours for today
        if et < t0_t:
            # Report end time is today before busines hours start, all done
            break

        if et < t1_t:
            # Report end time is today in the middle of busines hours, adjust
            t1_t = et

        if t1_t < st:
            # Report start time occurs today *after* business end, nothing today
            continue

        if t0_t < st:
            # Report start time occurs today in the middle of the business hours
            # Adjust t0
            t0_t = st

        t0 = datetime_to_seconds(t0_t)
        t1 = datetime_to_seconds(t1_t)

        #logger.debug("  START: %s  END: %s" % (str(t0_t), str(t1_t)))
        times.append([t0*1000, t1*1000, t1-t0])

    if len(times) == 0:
        return None
    else:
        return pandas.DataFrame(times, columns=['starttime', 'endtime', 'totalsecs'])


def report_business_hours(query, tables, criteria, params):
    times = tables['times']

    if times is None or len(times) == 0:
        return None

    deptable = Table.objects.get(id=params['table'])

    # Create all the jobs
    batch = BatchJobRunner(query)
    for i, row in times.iterrows():
        t0 = row['starttime']/1000
        t1 = row['endtime']/1000
        sub_criteria = copy.copy(criteria)
        sub_criteria.starttime = datetime.datetime.utcfromtimestamp(t0).replace(tzinfo=pytz.utc)
        sub_criteria.endtime = datetime.datetime.utcfromtimestamp(t1).replace(tzinfo=pytz.utc)

        job = Job.create(table=deptable, criteria=sub_criteria)
        logger.debug("Created %s: %s - %s" % (job, t0, t1))
        batch.add_job(job)

    if len(batch.jobs) == 0:
        return None

    # Run all the Jobs
    batch.run()

    # Now collect the data
    total_secs = 0
    df = None
    idx = 0
    for job in batch.jobs:
        if job.status == Job.ERROR:
            raise AnalysisException("%s for %s-%s failed: %s" %
                                    (job, job.criteria.starttime,
                                     job.criteria.endtime,
                                     job.message))
        subdf = job.data()
        logger.debug("%s: returned %d rows" %
                     (job, len(subdf) if subdf is not None else 0))
        if subdf is None:
            continue

        logger.debug("%s: actual_criteria %s" % (job, job.actual_criteria))
        t0 = job.actual_criteria.starttime
        t1 = job.actual_criteria.endtime
        subdf['__secs__'] = timedelta_total_seconds(t1 - t0)
        total_secs += timedelta_total_seconds(t1 - t0)
        idx += 1
        if df is None:
            df = subdf
        else:
            df = df.append(subdf)

    if df is None:
        return None

    keynames = [key.name for key in deptable.get_columns(iskey=True)]
    if 'aggregate' in params:
        ops = params['aggregate']
        for col in deptable.get_columns(iskey=False):
            if col.name not in ops:
                ops[col.name] = 'sum'

    else:
        ops = 'sum'

    df = avg_groupby_aggregate(df, keynames, ops, '__secs__', total_secs)

    return df


def avg_groupby_aggregate(df, keys, ops, t_col, total_t):
    """Groupby/aggregate with support for weighted averge column

    Group the data frame `df` on `keys` using the operation dict
    defined in `ops` just like the standard `df.aggregate(ops)`
    call, but support a `avg` operation that computes a
    weighted average using `weight_col` as the weight.

    This is used for aggregating multiple reports over different
    timeframes, where the rows from each report have a weight
    representing the time interval covered by the row in seconds.

    `df`       source pandas DataFrame

    `keys`     array of key column names

    `ops`      dict of operations to perform on each column.
               the key is the column, the value is either a
               numpy operation (et.sum, mean) or another function.
               Use 'avg' to compute the time weighted average

    `t_col`    the name of the column holding the time interval
               covered by each row

    `total_t`  the total time interval covered by all reports
               in the `df` source data

    For example, consider 3 queries over different intervals, the first
    is 1 hour (3600 seconds), the second and third both cover 8 hours
    (28800 seconds).  The results from each query are all in the
    same DataFrame.

    >>> q1_data = [['tcp',   72000,    20,          3600],
                   ['udp',   3600,     1,           3600],
                   ['icmp',  360,      0.1,         3600]]

    >>> q2_data = [['tcp',   1152000,  40,          28800],
                   ['udp',   57600,    2,           28800]]

    >>> q3_data = [['tcp',   1440000,  50,          28800],
                   ['udp',   201600,   7,           28800],
                   ['icmp',  8640,     0.3,         28800]]

    >>> data = q1_data.copy()
    >>> data.append(q2_data)
    >>> data.append(q3_data)

    >>> df = pandas.DataFrame(data, 
           columns = ['proto', 'bytes', 'avg_bytes', 'interval'])

    >>> avg_groupby_aggregate(df, ['proto'],
                               {'bytes': sum, 'avg_bytes': 'avg'},
                               'interval', 3600 + 28800 + 28800)

        proto     bytes    avg_bytes
    0    icmp      9000     0.147059
    1    tcp    2664000    43.529412
    2    udp     262800     4.294118

    """
    # The basic idea is to leverage the pandas aggregate() function, but
    # it works most simply column by column, whereas we need to
    # leverage the weight of each row as it may change.
    #
    # We can get this done by instead computing weighted value for each
    # row, using pandas to aggregate using sum on just the weighted sum
    # columns, and then dividing the resulting sums by the total interval
    #
    # Basic algorithm for a column x:
    #   1. Compute x__weighted__ == x * t_col for all rows
    #   2. Group by and aggregate the weighted cols by sum()
    #   3. Compute the resulted x = sum(x__weighted__) / total_t

    # Simple function to define a unique column name
    # for the weighted total column for an existing column name
    def weighted_col(name):
        return name + '__weighted__'

    # The ops dictionary defines the map of column names and the aggregation
    # function.  Iterate through this map
    newops = {}
    for k, v in ops.iteritems():
        if v == 'avg':
            df[weighted_col(k)] = df[k] * df[t_col]
            newops[weighted_col(k)] = 'sum'
        else:
            newops[k] = ops[k]

    result = df.groupby(keys).aggregate(newops).reset_index()
    for k, v in ops.iteritems():
        if v == 'avg':
            result[k] = result[weighted_col(k)] / total_t
            del result[weighted_col(k)]
            del df[weighted_col(k)]

    return result
