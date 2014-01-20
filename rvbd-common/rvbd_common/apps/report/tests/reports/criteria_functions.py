import pandas
import logging

logger = logging.getLogger(__name__)


def analysis_echo_criteria(query, tables, criteria, params):
    df = pandas.DataFrame([[str(k),str(v)]
                           for k,v in criteria.iteritems()],
                          columns=['key', 'value'])
    return df

def preprocess_field_choices(form, id, field_kwargs, params):
    field_kwargs['choices'] = [('val1', 'Value 1'),
                               ('val2', 'Value 2'),
                               ('val3', 'Value 3')]

def preprocess_field_choices_with_params(form, id, field_kwargs, params):
    choices = []
    for i in range(params['start'], params['end']+1):
        val = params['prefix'] + '_val' + str(i)
        choices.append((val, val))
        
    field_kwargs['choices'] = choices

def preprocess_changesecond(form, id, field_kwargs, params):
    first_val = form.get_field_value('first', id)
    field_kwargs['choices'] = [(first_val + ('-%d' % i), 'Choice %d' % i) for i in range(3)]
        
def postprocess_field_compute(form, id, criteria, params):
    s = 0
    for f in params['fields']:
        s = s + int(criteria[f])

    criteria[id] = s

def sharedfields_compute(form, id, criteria, params):
    criteria[id] = str(int(criteria['x']) * 2 + int(params['factor']))
    
def postprocesserrors_compute(form, id, criteria, params):
    if criteria['error'] == 'syntax':
        adsf
    else:
        criteria['x'] = 1
        
