def make_whois_link(ip):
    return '<a href="http://whois.arin.net/rest/nets;q=%s?showDetails=true&showARIN=false&ext=netref2" target="_blank">Whois record</a>' % ip

def whois(dst, src):
    '''Return a data frame that simply adds a whois link for each IP'''
    df = src['t']
    df['whois'] = df['host_ip'].map(make_whois_link)
    return df

