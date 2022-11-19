from dotenv import load_dotenv
from tmdbv3api import TMDb
import os

load_dotenv()
tmdb = TMDb()
tmdb.api_key = os.environ.get('TMDB_API_KEY')
