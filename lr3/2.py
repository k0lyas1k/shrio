from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get('https://www.news29.ru/novosti/')

element = driver.find_element(by=By.ID, value='mainContainer')
list_news = element.find_elements(by=By.CLASS_NAME, value='newItemContainer')

news: {int: {str: str}} = {}
count = 1
for i in range(len(list_news)):
    new = driver.find_elements(by=By.CLASS_NAME, value='newItemContainer')[i]
    title_news = new.find_element(by=By.CLASS_NAME, value='title')
    title_news.click()
    page = driver.find_element(by=By.CLASS_NAME, value='fulltext_eq_pad')
    news[i + 1] = {page.find_element(by=By.TAG_NAME, value='h1').text: page.find_element(by=By.CLASS_NAME, value='lead').text}
    driver.get('https://www.news29.ru/novosti/')


print(news)
