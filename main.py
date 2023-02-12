from DNSParser import DNSParser, Tag

if __name__ == '__main__':
    parser = DNSParser(parsingTags=[Tag.title, Tag.price, Tag.availability, Tag.description])

    parser.authorizationDNS("******", "******")
    #url ='https://www.dns-shop.ru/catalog/17a899cd16404e77/processory/?stock=now-today-tomorrow-later-out_of_stock&price=10001-18000&f[ykga]=1ii0xm'
    #parser.parseDNSCatalog(url, pages=999)
    # url = "https://www.dns-shop.ru/catalog/17a899cd16404e77/processory/?stock=now-today-tomorrow-later-out_of_stock&price=10001-18000&f[ykga]=1ii0xo"
    # parser.parseDNSCatalog(url, pages=999)
    url = 'https://www.dns-shop.ru/catalog/17a899cd16404e77/processory/?order=6'
    parser.parseDNSCatalog(url, pages=999)
    parser.exportData('paneliDns')
    del parser
