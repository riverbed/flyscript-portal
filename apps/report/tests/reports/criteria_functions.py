import pandas
import logging
import time
from apps.datasource.models import Job, Table, Column
from apps.datasource.modules.analysis import  AnalysisTable, AnalysisException

logger = logging.getLogger(__name__)


def criteria(query, tables, criteria, params):
    criteria.compute_times()
    df = pandas.DataFrame([[str(k),str(v)]
                           for k,v in criteria.iteritems()],
                          columns=['key', 'value'])
    return df

def preprocess_field_choices(field, field_kwargs, params):
    field_kwargs['choices'] = [('val1', 'Value 1'),
                               ('val2', 'Value 2'),
                               ('val3', 'Value 3')]

def preprocess_field_choices_with_params(field, field_kwargs, params):
    choices = []
    for i in range(params['start'], params['end']+1):
        val = params['prefix'] + '_val' + str(i)
        choices.append((val, val))
        
    field_kwargs['choices'] = choices

def postprocess_field_compute(field, criteria, params):
    s = 0
    for f in params['fields']:
        s = s + int(criteria[f])

    criteria[field.keyword] = s
