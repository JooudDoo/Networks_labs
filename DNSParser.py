import time
from dataclasses import dataclass
from typing import Callable, Optional, List
from enum import Enum

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
    serviceRating = 'serviceRating'
    specifications = 'specifications'
    reviewsCount = 'reviewsCount'

class ExtractingPlace(Enum):
    none = 0
    catalog = 1
    productPage = 2

class DNSParser():

    @dataclass
    class ProductData():
        name : str = ""
        price : str = ""
        availability : str = ""
        productLink : str = ""
        description : str = ""
        serviceRating : str = ""
        specifications : str = ""
        reviewsCount : str = ""
        def __repr__(self):
            return f'"{self.name}",{self.price}'
        def __str__(self):
            return f"{self.name}\n{self.price}\n"

    @dataclass
    class TagExtractor():
        name : str 
        extFunc : Callable[[str], str]
        description : Optional[str] = 'empty'
        extractingFrom : ExtractingPlace = ExtractingPlace.none
        default : Optional[str] = 'Not found'

    _tagsExtractorsDictionary = {
        Tag.title: TagExtractor('name', lambda data: data.find('a', attrs={"class": "catalog-product__name ui-link ui-link_black"}).find('span').get_text(), extractingFrom=ExtractingPlace.catalog),
        Tag.price: TagExtractor('price', lambda data: data.find('div', attrs={"class": "product-buy__price"}).get_text().split('₽')[0]+'₽', extractingFrom=ExtractingPlace.catalog),
        Tag.availability: TagExtractor('product availability', lambda data: data.find('div', attrs={"class": "order-avail-wrap"}).get_text().strip(), extractingFrom=ExtractingPlace.catalog),
        Tag.productLink: TagExtractor('link on product', lambda data: data.find('a', attrs={"class": "catalog-product__name"}).get('href'), extractingFrom=ExtractingPlace.catalog),
        Tag.serviceRating: TagExtractor('product service rating', lambda data: data.find('a', attrs={"class": "catalog-product__service-rating"}).get_text() + "%", extractingFrom=ExtractingPlace.catalog),
        Tag.reviewsCount: TagExtractor('number of reviews', lambda data: data.find('a', {"class": "catalog-product__rating"}).get_text(), extractingFrom=ExtractingPlace.catalog),

        Tag.description: TagExtractor('product description', lambda data: data.find('div', attrs={"class": "product-card-description-text"}).get_text(), extractingFrom=ExtractingPlace.productPage),
        Tag.specifications: TagExtractor('product specifications', lambda data: data.find('div', attrs={"class": "product-characteristics"}).get_text(), extractingFrom=ExtractingPlace.productPage)
    }

    LOW_PRIORITY_TAGS = [Tag.serviceRating, Tag.reviewsCount, Tag.specifications]
    RETRY_ATTEMPTS = 5
    DNS_MAIN_PAGE = 'https://www.dns-shop.ru'
    DNS_LOGIN_PAGE = 'https://www.dns-shop.ru/profile/menu/'

    def __init__(self, parsingTags : List[Tag] = [Tag.title, Tag.price, Tag.availability]):
        self._parsingExportTags = parsingTags.copy()
        self._parsingTags = parsingTags.copy()
        self._parsedProducts : List[self.ProductData] = []
        self._extractFromPrPg = False
        self._verifyTags()
        options = webdriver.ChromeOptions()
        options.add_argument('log-level=3')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        self._driver = webdriver.Chrome(options=options)
        self._driver.maximize_window()
    
    def _verifyTags(self):
        for tag in self._parsingTags:
            if self._getTagExtractor(tag).extractingFrom == ExtractingPlace.productPage and not self._extractFromPrPg: 
                self._extractFromPrPg = True
                if Tag.productLink not in self._parsingTags:
                    self._parsingTags.append(Tag.productLink)

    def __del__(self):
        self._driver.close()
        self._driver.quit()
    
    def _applyTagExtractor(self, data : str, tag : Tag) -> str:
        tagExtractor = self._tagsExtractorsDictionary[tag]
        try:
            return tagExtractor.extFunc(data)
        except:
            if tag in self.LOW_PRIORITY_TAGS:
                return tagExtractor.default
            raise Exception(f"Couldn't exctract tag {tag.value}")
    
    def _getTagExtractor(self, tag : Tag) -> TagExtractor:
        return self._tagsExtractorsDictionary[tag]
    
    def _extractCatalogViaSoup(self, pageSource : str) -> List[ProductData]:
        soup = BeautifulSoup(pageSource, "html.parser")
        products = soup.find_all(attrs={"data-id": "product"})
        productsData : list[self.ProductData] = []
        for product in products:
            productData = self.ProductData()
            for tag in self._parsingTags:
                if self._getTagExtractor(tag).extractingFrom == ExtractingPlace.catalog:
                    tagData = self._applyTagExtractor(product, tag)
                    setattr(productData, tag.value, tagData)
            productsData.append(productData)
        return productsData
    
    def _extractPrPageViaSoup(self, pageSource : str, product : ProductData = ProductData()) -> List[ProductData]:
        soup = BeautifulSoup(pageSource, "html.parser")
        for tag in self._parsingTags:
            if self._getTagExtractor(tag).extractingFrom == ExtractingPlace.productPage:
                setattr(product, tag.value, self._applyTagExtractor(soup, tag))
        return product

    def _productsInCategory(self):
        return int(self._driver.find_element(By.CLASS_NAME, "products-count").text.split()[0])

    def _clickPageLink(self):
        try:
            nextPageLink = self._driver.find_element(By.CLASS_NAME, 'pagination-widget__page-link_next')
        except:
            return False
        if "pagination-widget__page-link_disabled" in nextPageLink.get_attribute('class'):
            return False
        nextPageLink.click()
        return True
    
    def _removeDuplicatesList(self, list):
        newList = []
        for elem in list:
            if elem not in newList:
                newList.append(elem)
        return newList

    def _extractCatalogs(self, url : str, pages : int, products : List[ProductData] = []) -> List[ProductData]:
        self._driver.get(url)
        time.sleep(0.1)
        productsCount = self._productsInCategory()
        print(f"\tExtracting catalogs...")
        progressBar = tqdm(total=productsCount)
        badCycleCount = 0
        while pages:
            time.sleep(0.6)
            try:
                productsData = self._extractCatalogViaSoup(self._driver.page_source)
                nextPageReady = self._clickPageLink()
            except:
                badCycleCount += 1
                if badCycleCount > self.RETRY_ATTEMPTS:
                    if not self._clickPageLink():
                        print(f"Reached max attemps count")
                        pages = 0
                continue
            products += productsData
            progressBar.update(len(productsData))
            pages -= 1
            badCycleCount = 0
            if not nextPageReady:
                pages = 0
        progressBar.close()
        return self._removeDuplicatesList(products)

    def _isProductParsedByPlace(self, product : ProductData, place : ExtractingPlace) -> bool:
        for tag in self._parsingTags:
            field = getattr(product, tag.value)
            if field == "" and self._getTagExtractor(tag).extractingFrom == place:
                return False
        return True
            
    def _extractPrPages(self, products : List[ProductData]) -> List[ProductData]:
        print(f"\tExtracting product pages...")

        class LoadNext():
            def __init__(self, remainProductsCnt, progressBar):
                self.badCycleCount = 0
                self.currentProductNumber = 0
                self.remainProductsCnt = remainProductsCnt
                self.progressBar = progressBar
                self._chunkLoadCount = 10
                self._currentChunk = 0
            
            def moveToNextProduct(self):
                self._currentChunk += 1
                if self._chunkLoadCount == self._currentChunk:
                    time.sleep(2)
                    self._currentChunk = 0
                self.badCycleCount = 0
                self.currentProductNumber += 1
                self.remainProductsCnt -= 1
                self.progressBar.update(1)
            
        remainProductsCnt = len(products)
        currentProductNumber = 0
        progressBar = tqdm(total=remainProductsCnt)
        product = products[currentProductNumber]
        self._driver.get(self.DNS_MAIN_PAGE+product.productLink)

        loader = LoadNext(remainProductsCnt, progressBar)

        while loader.remainProductsCnt:
            if loader.badCycleCount == 0 or loader.badCycleCount >= self.RETRY_ATTEMPTS:
                product = products[loader.currentProductNumber]
                if self._isProductParsedByPlace(product, ExtractingPlace.productPage):
                    loader.moveToNextProduct()
                    continue
                self._driver.get(self.DNS_MAIN_PAGE+product.productLink)
            time.sleep(0.35)
            try:
                product = self._extractPrPageViaSoup(self._driver.page_source, product)
            except:
                loader.badCycleCount += 1
                continue
            loader.moveToNextProduct()
        progressBar.close()
        return products

    def exportData(self, filePath : str) -> None:
        print(f"Start data export")
        csvFilePath = filePath
        if not csvFilePath.endswith('.csv'):
            csvFilePath += '.csv'
        with open(csvFilePath, 'w', encoding='utf8') as exportFile:
            for ind, tag in enumerate(self._parsingExportTags):
                exportFile.write(self._tagsExtractorsDictionary[tag].name)
                exportFile.write(',' if ind != len(self._parsingExportTags)-1 else '')
            exportFile.write('\n')
            for product in self._parsedProducts:
                for ind, productTag in enumerate(self._parsingExportTags):
                    exportFile.write(f'"{getattr(product, productTag.value)}"')
                    exportFile.write("," if ind != len(self._parsingExportTags)-1 else "")
                exportFile.write('\n')
        print(f"Data sucessfuly exported to {csvFilePath}")

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

    def parseDNSCatalog(self, url : str, pages : int) -> None:
        self._extractCatalogs(url, pages, self._parsedProducts)

        if self._extractFromPrPg:
            self._parsedProducts = self._extractPrPages(self._parsedProducts)