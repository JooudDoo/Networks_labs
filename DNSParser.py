import time
from dataclasses import dataclass
from typing import Callable, Optional, List
from enum import Enum

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from tqdm import tqdm
from bs4 import BeautifulSoup

class Tag(Enum):
    title = 'name'
    price = 'price'
    availability = 'availability'
    productLink = 'productLink'
    description = 'description'

class DNSParser():

    @dataclass
    class ProductData():
        name : str = ""
        price : str = ""
        availability : str = ""
        productLink : str = ""
        description : str = ""
        def __repr__(self):
            return f'"{self.name}",{self.price}'
        def __str__(self):
            return f"{self.name}\n{self.price}\n"

    @dataclass
    class TagExtractor():
        name : str 
        extFunc : Callable[[str], str]
        description : Optional[str] = 'empty'
        extractingInCatalog : bool = True

    _tagsExtractorsDictionary = {
        Tag.title: TagExtractor('product name', lambda data: data.find('a', attrs={"class": "catalog-product__name ui-link ui-link_black"}).find('span').get_text(), extractingInCatalog=True),
        Tag.price: TagExtractor('product price', lambda data: data.find('div', attrs={"class": "product-buy__price"}).get_text(), extractingInCatalog=True),
        Tag.availability: TagExtractor('product available', lambda data: "Нет в наличии" if data.find('div', attrs={"class": "order-avail-wrap_not-avail"}) else "В наличии", extractingInCatalog=True),
        Tag.productLink: TagExtractor('link on product', lambda data: data.find('a', attrs={"class": "catalog-product__name"}).get_text(), extractingInCatalog=True),
        Tag.description: TagExtractor('product description', lambda data: data, extractingInCatalog=False)
    }

    DNS_LOGIN_PAGE = 'https://www.dns-shop.ru/profile/menu/'

    def __init__(self, parsingTags : List[Tag] = [Tag.title, Tag.price, Tag.availability]):
        self._parsingExportTags = parsingTags
        self._parsingTags = parsingTags
        self._parsedProducts : list[self.ProductData] = []
        self._extractProductDescription = False
        self._verifyTags()
        options = webdriver.ChromeOptions()
        #options.add_argument('log-level=3') # options=options
        self._driver = webdriver.Chrome()
        self._driver.maximize_window()
    
    def _verifyTags(self):
        if Tag.description in self._parsingTags: 
            self._extractProductDescription = True
            if Tag.productLink not in self._parsingTags:
                self._parsingTags.append(Tag.productLink)

    def __del__(self):
        self._driver.close()
        self._driver.quit()
    
    def _applyTagExtractor(self, data : str, tag : Tag) -> str:
        tagExtractor = self._tagsExtractorsDictionary[tag]
        if tagExtractor.extractingInCatalog:
            return tagExtractor.extFunc(data)
        else:
            return None
    
    def _extractViaSoup(self, pageSource : str) -> List[ProductData]:
        soup = BeautifulSoup(pageSource, "html.parser")
        products = soup.find_all(attrs={"data-id": "product"})
        productsData : list[self.ProductData] = []
        for product in products:
            productData = self.ProductData()
            for tag in self._parsingTags:
                print(tag)
                tagData = self._applyTagExtractor(product, tag)
                setattr(productData, tag.value, tagData)
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
            for ind, tag in enumerate(self._parsingExportTags):
                exportFile.write(f"{tag.value}{',' if ind != len(self._parsingTags)-1 else ''}")
            exportFile.write('\n')
            for product in self._parsedProducts:
                for ind, productTag in enumerate(self._parsingExportTags):
                    exportFile.write(f"{getattr(product, productTag.value)}{',' if ind != len(self._parsingTags)-1 else ''}")
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
