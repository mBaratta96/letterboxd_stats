from selenium import webdriver
from selenium.webdriver.common.by import By

web = webdriver.Firefox()
web.implicitly_wait(10)
web.get("https://letterboxd.com/")
web.find_element(By.CLASS_NAME, "fc-cta-do-not-consent").click()
sign_in_button = web.find_element(By.CLASS_NAME, "sign-in-menu")
print(sign_in_button)
