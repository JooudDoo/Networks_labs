from DNSParser import DNSParser, Tag

if __name__ == '__main__':
    parser = DNSParser(parsingTags=[Tag.title, Tag.price, Tag.availability])
    url = 'https://www.dns-shop.ru/catalog/17a899cd16404e77/processory/?order=6'
    parser.authorizationDNS("******", "")
    parser.parseDNSUrlCatalog(url, pages=999)
    parser.exportData('paneliDns')
    del parser
