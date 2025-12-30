import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TENANT_FOLDER = os.path.join(BASE_DIR, "tenants")
os.makedirs(TENANT_FOLDER, exist_ok=True)

SECRET_KEY = os.getenv("SECRET_KEY", "hrms-secret-key")
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "hrms.com")

# Master database (SQLite for now, can switch to PostgreSQL)
MASTER_DB = f"sqlite:///{os.path.join(BASE_DIR, 'master.db')}"

class Config:
    SQLALCHEMY_DATABASE_URI = MASTER_DB
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_BINDS = {}
    SECRET_KEY = SECRET_KEY