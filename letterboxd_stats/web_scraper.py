import os
from zipfile import ZipFile
from config import config
import requests

class Downloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.get("https://letterboxd.com")

    def login(self):
        res = self.session.post("https://letterboxd.com/user/login.do", data={
            'username': config['Letterboxd']['username'],
            'password': config['Letterboxd']['password'],
            '__csrf': self.session.cookies.get_dict()['com.xk72.webparts.csrf']
        })
        if res.json()["result"] != "success":
            raise ConnectionError("Impossible to login")

    def download_stats(self):
        res = self.session.get("https://letterboxd.com/data/export/")
        if res.status_code != 200 or "application/zip" not in res.headers['Content-Type']:            
            raise ConnectionError(f"Impossible to download data. Response headers:\n{res.headers}")
        print("Data download successful.")
        filename = res.headers["content-disposition"].split()[-1].split("=")[-1]
        path = os.path.expanduser(os.path.join(config["root_folder"], "static"))
        archive = os.path.join(path, filename)
        with open(archive, "wb") as f:
            f.write(res.content)
        with ZipFile(archive, "r") as zip:
            zip.extractall(path)
        os.remove(archive)

