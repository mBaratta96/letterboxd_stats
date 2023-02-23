import tomli
import os

path = os.path.abspath("./config/config.toml")
with open(path, "rb") as f:
    config = tomli.load(f)
