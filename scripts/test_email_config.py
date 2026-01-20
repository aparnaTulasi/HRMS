import smtplib
import os
from dotenv import load_dotenv

# Load .env from project root (assuming script is in scripts/ folder)
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

def test_email():
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "tulasiseelam9@gmail.com" # Matches your config
    sender_password = os.getenv("MAIL_PASSWORD")
    
    print(f"--- Email Configuration Test ---")
    print(f"Loading .env from: {os.path.abspath(env_path)}")
    print(f"User: {sender_email}")
    print(f"Password Loaded: {'YES' if sender_password else 'NO'}")

    if not sender_password:
        print("❌ Error: MAIL_PASSWORD not found in .env file.")
        return

    try:
        print(f"Connecting to {smtp_server}:{smtp_port}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("Attempting login...")
        server.login(sender_email, sender_password)
        print("✅ Login successful! Your credentials are correct.")
        server.quit()
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("Tip: Ensure you are using a 16-digit Google App Password, not your login password.")

if __name__ == "__main__":
    test_email()