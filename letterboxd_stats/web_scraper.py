import os
from zipfile import ZipFile
from config import config
import requests

class Downloader:
    def download_stats(self):
        cookies = config['Letterboxd']['cookies']
        print(cookies)
        res = requests.get("https://letterboxd.com/data/export/", cookies=cookies)
        if res.status_code != 200:
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
