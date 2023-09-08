import time
from dataclasses import dataclass
from typing import Callable, Optional, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FXService
from tqdm import tqdm
from bs4 import BeautifulSoup


class DNSParser():

    @dataclass
    class ProductData():
        name : str = ""
        price : str = ""
        availability : str = ""
        def __repr__(self):
            return f'"{self.name}",{self.price}'
        def __str__(self):
            return f"{self.name}\n{self.price}\n"

    @dataclass
    class TagExtractor():
        name : str 
        extFunc : Callable[[str], str]
        description : Optional[str] = 'empty'

    _tagsExtractorsDictionary = {
        "name": TagExtractor('product name', lambda data: data.find('a', attrs={"class": "catalog-product__name ui-link ui-link_black"}).find('span').get_text()),
        "price": TagExtractor('product price', lambda data: data.find('div', attrs={"class": "product-buy__price"}).get_text()),
        "availability": TagExtractor('product available', lambda data: "Нет в наличии" if data.find('div', attrs={"class": "order-avail-wrap_not-avail"}) else "В наличии")
    }

    DNS_LOGIN_PAGE = 'https://www.dns-shop.ru/profile/menu/'

    def __init__(self, parsingTags : List[str] = ['name', 'price', 'availability']):
        self._parsingTags = parsingTags
        self._parsedProducts : list[self.ProductData] = []
        options = webdriver.ChromeOptions()
        # options.binary_location = "/usr/bin/firefox-esr"
        options.add_argument('log-level=3')
        # options.add_argument('--headless')
        options.add_argument('user-agent=fake-useragent')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument('--start-maximized')
        options.add_argument('--no-sandbox')

        self._driver = webdriver.Chrome(options=options)
        self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            'source': '''
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        '''
        })
        self._driver.maximize_window()
    
    def __del__(self):
        self._driver.close()
        self._driver.quit()
    
    def _applyTagExtractor(self, data : str, tag : str) -> str:
        return self._tagsExtractorsDictionary[tag].extFunc(data)
    
    def _extractViaSoup(self, pageSource : str) -> List[ProductData]:
        soup = BeautifulSoup(pageSource, "html.parser")
        products = soup.find_all(attrs={"data-id": "product"})
        productsData : list[self.ProductData] = []
        for product in products:
            productData = self.ProductData()
            for tag in self._parsingTags:
                tagData = self._applyTagExtractor(product, tag)
                setattr(productData, tag, tagData)
            productsData.append(productData)
        return productsData
    
    def _clickPageLink(self):
        try:
            nextPageLink = self._driver.find_element(By.CLASS_NAME, 'pagination-widget__page-link_next')
        except:
            return False
        if "pagination-widget__page-link_disabled" in nextPageLink.get_attribute('class'):
            return False
        nextPageLink.click()
        return True
    
    def exportData(self, filePath : str) -> None:
        print(f"Start data export")
        csvFilePath = filePath
        if not csvFilePath.endswith('.csv'):
            csvFilePath += '.csv'
        with open(csvFilePath, 'w', encoding='utf8') as exportFile:
            for ind, tag in enumerate(self._parsingTags):
                exportFile.write(f"{tag}{',' if ind != len(self._parsingTags)-1 else ''}")
            exportFile.write('\n')
            for product in self._parsedProducts:
                for ind, productTag in enumerate(self._parsingTags):
                    exportFile.write(f"{getattr(product, productTag)}{',' if ind != len(self._parsingTags)-1 else ''}")
                exportFile.write('\n')
        print(f"Data sucessfuly exported to {csvFilePath}")
    
    def _productsInCategory(self):
        return int(self._driver.find_element(By.CLASS_NAME, "products-count").text.split()[0])

    def authorizationDNS(self, login : str, password : str) -> None:
        self._driver.get(self.DNS_LOGIN_PAGE)
        time.sleep(0.5)
        loginButton = self._driver.find_element(By.CLASS_NAME, "user-page__login-btn")
        loginButton.click()
        loginWithPassBtn = self._driver.find_element(By.CLASS_NAME, "block-other-login-methods__password-caption")
        loginWithPassBtn.click()
        time.sleep(0.2)
        loginInputField = self._driver.find_element(By.CLASS_NAME, "form-entry-with-password__input").find_element(By.TAG_NAME, 'input')
        loginInputField.send_keys(login)
        passwordInputField = self._driver.find_element(By.CLASS_NAME, "form-entry-with-password__password").find_element(By.TAG_NAME, 'input')
        passwordInputField.send_keys(password)
        submitButton = self._driver.find_element(By.CLASS_NAME, "form-entry-with-password__main-button").find_element(By.TAG_NAME, "button")
        time.sleep(0.2)
        submitButton.click()
        time.sleep(0.4)

    def parseDNSUrlCatalog(self, url : str, pages : int) -> None:
        self._driver.get(url)
        time.sleep(5)
        with open("html.html", 'w', encoding='utf8') as f:
            f.write(self._driver.page_source)
        productsCount = self._productsInCategory()
        progressBar = tqdm(total=productsCount)
        badCycleCount = 0
        while pages and badCycleCount <= 5:
            time.sleep(0.6)
            try:
                productsData = self._extractViaSoup(self._driver.page_source)
                nextPageReady = self._clickPageLink()
            except:
                badCycleCount += 1
                continue
            self._parsedProducts += productsData
            progressBar.update(len(productsData))
            pages -= 1
            badCycleCount = 0
            if not nextPageReady:
                pages = 0
        progressBar.close()


if __name__ == '__main__':
    parser = DNSParser(parsingTags=['name', 'price', 'availability'])
    url = 'https://www.dns-shop.ru/catalog/17a899cd16404e77/processory/?order=6'
    #parser.authorizationDNS("******, "******")
    parser.parseDNSUrlCatalog(url, pages=999)
    parser.exportData('paneliDns')
    del parser

