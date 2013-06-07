def whois(dst, src):
    print "---------------In whois"
    df = src['t']
    df['whois'] = df['host_ip'].map(lambda x: '<a href="http://whois.arin.net/rest/nets;q=%s?showDetails=true&showARIN=false&ext=netref2">Whois record</a>' % x)
    print df[:10]
    return df

