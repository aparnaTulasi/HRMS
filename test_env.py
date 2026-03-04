import os
from dotenv import load_dotenv  # pyre-ignore[21]
from config import Config  # pyre-ignore[21]

# Explicitly load .env from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def test_config():
    print(f"SECRET_KEY: {Config.SECRET_KEY}")
    print(f"DATABASE_URI: {Config.SQLALCHEMY_DATABASE_URI}")
    print(f"MAIL_USERNAME: {Config.MAIL_USERNAME}")
    print(f"MAIL_PASSWORD: {'SET' if Config.MAIL_PASSWORD else 'NOT SET'}")

if __name__ == "__main__":
    test_config()
