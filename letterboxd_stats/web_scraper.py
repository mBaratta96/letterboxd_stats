from selenium import webdriver
from selenium.webdriver.common.by import By
import os

web = webdriver.Firefox()
web.implicitly_wait(10)
web.get("https://letterboxd.com/")
web.find_element(By.CLASS_NAME, "fc-cta-do-not-consent").click()

def login():
    sign_in_button = web.find_element(By.CLASS_NAME, "sign-in-menu")
    sign_in_button.click()
    username_input = web.find_element(By.ID, 'username')
    username_input.send_keys(os.environ['LETTERBOXD_USERNAME'])
    password_input = web.find_element(By.ID, 'password')
    password_input.send_keys(os.environ['LETTERBOXD_PASSWORD'])
    web.find_element(By.CLASS_NAME, "button-container").click()
