import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def _send_html_email(to_email: str, subject: str, html_body: str) -> bool:
    try:
        sender_email = current_app.config["MAIL_USERNAME"]
        sender_password = current_app.config["MAIL_PASSWORD"]
        smtp_server = current_app.config["MAIL_SERVER"]
        smtp_port = current_app.config["MAIL_PORT"]

        if not all([sender_email, sender_password, smtp_server, smtp_port]):
            print("❌ Mail config missing. Check .env + Config.py")
            return False

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

        print("✅ Email sent to:", to_email)
        return True

    except Exception as e:
        print("❌ Email send failed:", e)
        return False


def send_login_credentials(to_email, password, login_url):
    subject = "Your HRMS Admin Credentials"
    body = f"""
    <h3>Welcome to HRMS</h3>
    <p>Your company account has been created successfully.</p>
    <p><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></p>
    <p><strong>Username:</strong> {to_email}</p>
    <p><strong>Password:</strong> {password}</p>
    <br>
    <p>Please login and change your password immediately.</p>
    """
    return _send_html_email(to_email, subject, body)


def send_otp_email(to_email, otp):
    subject = "Your HRMS Verification OTP"
    body = f"""
    <h3>HRMS Verification</h3>
    <p>Your One Time Password (OTP) is:</p>
    <h2>{otp}</h2>
    <p>This OTP is valid for 10 minutes.</p>
    """
    return _send_html_email(to_email, subject, body)
