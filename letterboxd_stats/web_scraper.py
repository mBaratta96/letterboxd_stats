from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from zipfile import ZipFile
from config import config


profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.manager.showWhenStarting", False)
profile.set_preference("browser.download.dir", os.path.join(
    config['root_folder'], 'static')
)
profile.set_preference(
    "browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")

options = Options()
options.add_argument("--headless")

web = webdriver.Firefox(firefox_profile=profile, options=options)
web.implicitly_wait(10)
web.get("https://letterboxd.com/")
web.find_element(By.CLASS_NAME, "fc-cta-do-not-consent").click()


def login():
    sign_in_button = web.find_element(By.CLASS_NAME, "sign-in-menu")
    sign_in_button.click()
    username_input = web.find_element(By.ID, 'username')
    username_input.send_keys(config['Letterboxd']['username'])
    password_input = web.find_element(By.ID, 'password')
    password_input.send_keys(config['Letterboxd']['password'])
    web.find_element(By.CLASS_NAME, "button-container").click()
    print("Login successful")


def download_stats():
    nav_account = web.find_element(By.CLASS_NAME, "nav-account")
    ActionChains(web).move_to_element(nav_account).perform()
    web.find_element(By.LINK_TEXT, 'Settings').click()
    web.find_element(By.XPATH, "//a[@data-id='data']").click()
    web.find_element(By.CLASS_NAME, 'export-data-link').click()
    WebDriverWait(web, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, 'export-data-button'))
    ).click()
    time.sleep(5)
    print("Data download successful")


def extract_data():
    archive = None
    path = os.path.expanduser(os.path.join(
        config['root_folder'], 'static'
    ))
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file() and entry.name.endswith(".zip") \
                    and entry.name.startswith('letterboxd'):
                archive = entry.path
                break
    if not archive:
        raise FileNotFoundError("No Letterboxd .zip file found.")
    with ZipFile(archive, 'r') as zip:
        zip.extractall(path)
    os.remove(archive)


def close_webdriver():
    web.quit()
