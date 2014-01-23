import pandas
import logging

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


def explode_interface_dns(interface_dns):
    parts = interface_dns.split("|")
    ip = parts[0]
    ifindex = parts[2]
    return ip, ifindex


def process_join_ip_device(target, tables, criteria, params):
    dev = tables['devices']
    traffic = tables['traffic']

    if traffic is None or len(traffic) == 0:
        return None

    if dev is None or len(dev) == 0:
        return traffic

    dev = dev.copy()
    traffic['interface_ip'], traffic['interface_index'] = zip(*traffic['interface_dns'].
                                                              map(explode_interface_dns))

    # Set the name to the ip addr wherever the name is empty
    dev.ix[dev['name'] == '', 'name'] = dev.ix[dev['name'] == '', 'ipaddr']

    df = pandas.merge(traffic, dev, left_on='interface_ip', right_on='ipaddr', how='left')
    df = df.rename(columns={'name': 'interface_name'})

    return df
