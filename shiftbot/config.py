import os
from dotenv import load_dotenv

def get_url():
    load_dotenv()
    return os.getenv("DATABASE_URL")