import os 
from dotenv import load_dotenv

load_dotenv() # reads .env and loads its values into the environment

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # 1 hour
