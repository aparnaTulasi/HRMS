import os
from dotenv import load_dotenv

load_dotenv() 

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "hrms-secret-key-change-this")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_DIR, 'hrms.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    BASE_URL = "http://localhost:5000"

    # Email Configuration
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_PORT = 587
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)