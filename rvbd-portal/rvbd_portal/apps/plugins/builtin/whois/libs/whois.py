# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

def make_whois_link(ip):
    return '<a href="http://whois.arin.net/rest/nets;q=%s?showDetails=true&showARIN=false&ext=netref2" target="_blank">Whois record</a>' % ip

def whois(target, tables, criteria, params):
    '''Return a data frame that simply adds a whois link for each IP'''
    df = tables['t']
    df['whois'] = df['host_ip'].map(make_whois_link)
    return df

