import pandas
import logging
import datetime
import re, string
import random
import time
import copy
import pytz

logger = logging.getLogger(__name__)

def process_interface_dns_elem(interface_dns):
    parts = interface_dns.split("|")
    ip = parts[0]
    name = parts[1]
    ifindex = parts[2]
    if name is not "":
        return name + ":" + ifindex
    else:
        return ip + ":" + ifindex

def process_interface_dns(target, tables, criteria, params):
    table = tables['table']
    table['interface_dns'] = table['interface_dns'].map(process_interface_dns_elem)
    return table
