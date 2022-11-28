from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from zipfile import ZipFile
from config import config
import requests

profile = webdriver.FirefoxProfile()
profile.set_preference("browser.download.folderList", 2)
profile.set_preference("browser.download.manager.showWhenStarting", False)
profile.set_preference("browser.download.dir", os.path.join(config["root_folder"], "static"))
profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")

options = Options()
options.add_argument("--headless")


class FirefoxWebDriver:
    def __init__(self):
        self.web = webdriver.Firefox(firefox_profile=profile, options=options)
        self.web.implicitly_wait(10)
        self.web.get("https://letterboxd.com/")
        self.web.find_element(By.CLASS_NAME, "fc-cta-do-not-consent").click()

    def login(self):
        sign_in_button = self.web.find_element(By.CLASS_NAME, "sign-in-menu")
        sign_in_button.click()
        username_input = self.web.find_element(By.ID, "username")
        username_input.send_keys(config["Letterboxd"]["username"])
        password_input = self.web.find_element(By.ID, "password")
        password_input.send_keys(config["Letterboxd"]["password"])
        self.web.find_element(By.CLASS_NAME, "button-container").click()
        print("Login successful")

    def download_stats(self):
        nav_account = self.web.find_element(By.CLASS_NAME, "nav-account")
        ActionChains(self.web).move_to_element(nav_account).perform()
        self.web.find_element(By.LINK_TEXT, "Settings").click()
        self.web.find_element(By.XPATH, "//a[@data-id='data']").click()
        self.web.find_element(By.CLASS_NAME, "export-data-link").click()
        WebDriverWait(self.web, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "export-data-button")))
        cookies = {cookie["name"]: cookie["value"] for cookie in self.web.get_cookies()}
        res = requests.get("https://letterboxd.com/data/export/", cookies=cookies)
        if res.status_code != 200:
            self.close_webdriver()
            raise ConnectionError("Impossible to download data.")
        print("Data download successful.")
        filename = res.headers["content-disposition"].split()[-1].split("=")[-1]
        path = os.path.expanduser(os.path.join(config["root_folder"], "static"))
        archive = os.path.join(path, filename)
        with open(archive, "wb") as f:
            f.write(res.content)
        with ZipFile(archive, "r") as zip:
            zip.extractall(path)
        os.remove(archive)

    def close_webdriver(self):
        self.web.quit()
