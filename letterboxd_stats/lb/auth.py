import requests
from .utilities import LB_BASE_URL, LOGIN_URL

class LBAuth:
    def __init__(self, username=None, password=None):
        self.session = requests.Session()
        self.session.get(LB_BASE_URL)
        self.logged_in = False
        self.username = username
        self.password = password

    def login(self):
        payload = {
            "username": self.username, 
            "password": self.password, 
            "__csrf": self.get_csrf_token()
        }
        res = self.session.post(LOGIN_URL, data=payload)
        if res.json().get("result") != "success":
            raise ConnectionError("Login failed")
        self.logged_in = True

    def get_csrf_token(self):
        return self.session.cookies.get("com.xk72.webparts.csrf")