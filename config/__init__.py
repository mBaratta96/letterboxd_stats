import tomli
import os

path = os.path.abspath('./config.toml')
with open(path, "rb") as f:
    config = tomli.load(f)
