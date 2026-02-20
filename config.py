import os
from dotenv import load_dotenv

load_dotenv()

class Config :
    
    PROJECT_NAME      = "BACKEND PRACTICE"
    PROJECT_VERSION   = "1.0.0"
    POSTGRES_USER     = os.getenv("DB_USER")
    POSTGRES_PASSWORD = os.getenv("DB_PASSWORD")
    POSTGRES_SERVER   = os.getenv ("DB_SERVER")
    POSTGRES_PORT     = os.getenv("DB_PORT")
    POSTGRES_DB       = os.getenv("DB_NAME")
    DATABASE_URL      = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"


config = Config()
print (Config.DATABASE_URL)