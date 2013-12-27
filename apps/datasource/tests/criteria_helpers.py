import pandas

def criteria(query, tables, criteria, params):
    df = pandas.DataFrame([[str(k),str(v)]
                           for k,v in criteria.iteritems()],
                          columns=['key', 'value'])
    return df
