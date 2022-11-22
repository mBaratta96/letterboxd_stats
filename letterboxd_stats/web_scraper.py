from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time

profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.manager.showWhenStarting", False)
profile.set_preference("browser.download.dir", os.path.join(os.environ['ROOT_FOLDER'], 'static'))
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")

web = webdriver.Firefox(firefox_profile=profile)
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

def download_stats():
    nav_account = web.find_element(By.CLASS_NAME, "nav-account")
    ActionChains(web).move_to_element(nav_account).perform()
    web.find_element(By.LINK_TEXT, 'Settings').click()
    web.find_element(By.XPATH, "//a[@data-id='data']").click()
    web.find_element(By.CLASS_NAME, 'export-data-link').click()
    WebDriverWait(web, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, 'export-data-button'))).click()
    time.sleep(10)
