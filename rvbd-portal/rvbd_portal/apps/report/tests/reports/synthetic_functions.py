import logging

import pandas
from rvbd.common.timeutils import datetime_to_seconds


logger = logging.getLogger(__name__)

def analysis_generate_data(query, tables, criteria, params):
    t0 = datetime_to_seconds(criteria.starttime)
    t1 = datetime_to_seconds(criteria.endtime)

    data = []
    for t in range(t0, t1, params['source_resolution']):
        data.append([t, 1])

    df = pandas.DataFrame(data, columns=['time', 'value'])
    df['time'] = pandas.DatetimeIndex(df['time']*1000000000)
    return df

