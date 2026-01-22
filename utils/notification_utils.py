import smtplib
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_async_email(msg):
    """Sends email in a separate thread to avoid blocking the main application."""
    # Use environment variables for credentials, fallback to hardcoded for dev if needed
    sender_email = os.getenv("MAIL_USERNAME", "tulasiseelam9@gmail.com")
    password = os.getenv("MAIL_PASSWORD")

    if not password:
        print("⚠️ MAIL_PASSWORD not set. Skipping login notification email.")
        return

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Login notification sent to {msg['To']}")
    except Exception as e:
        print(f"❌ Error sending login notification: {e}")

def send_login_notification(to_email, ip_address):
    """Constructs the login notification email and starts the sending thread."""
    subject = "Security Alert: New Login Detected"
    
    body = f"""
    <html>
    <body>
        <h3>New Login Detected</h3>
        <p>Hello,</p>
        <p>We detected a new login to your HRMS account.</p>
        <ul>
            <li><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
            <li><strong>IP Address:</strong> {ip_address or 'Unknown'}</li>
        </ul>
        <p>If this was you, you can ignore this email.</p>
        <p>If you did not log in, please contact support immediately.</p>
        <br>
        <p>Regards,<br>HRMS Team</p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = os.getenv("MAIL_USERNAME", "HRMS Security")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    # Run in separate thread
    thread = threading.Thread(target=send_async_email, args=(msg,))
    thread.start()