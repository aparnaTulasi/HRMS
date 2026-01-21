import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def _send_plain_email(to_email: str, subject: str, body: str) -> bool:
    """
    Internal helper: sends email using SMTP config from Flask current_app.config
    """
    smtp_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(current_app.config.get("MAIL_PORT", 587))
    smtp_user = current_app.config.get("MAIL_USERNAME")
    smtp_pass = current_app.config.get("MAIL_PASSWORD")

    if not smtp_user or not smtp_pass:
        print("❌ Mail credentials missing (MAIL_USERNAME / MAIL_PASSWORD).")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=50)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


# -------------------------
# OTP Emails (Super Admin)
# -------------------------
def send_signup_otp(to_email: str, otp: str) -> bool:
    subject = "Super Admin Signup OTP"
    body = f"Your signup OTP is: {otp}\n\nValid for 10 minutes."
    return _send_plain_email(to_email, subject, body)


def send_reset_otp(to_email: str, otp: str) -> bool:
    subject = "Super Admin Password Reset OTP"
    body = f"Your password reset OTP is: {otp}\n\nValid for 10 minutes."
    return _send_plain_email(to_email, subject, body)


# --------------------------------
# Login Credentials Email (Admin/HR/Employee)
# --------------------------------
def send_login_credentials(email: str, password: str, login_url: str) -> bool:
    subject = "Your HRMS Login Credentials"
    body = (
        "Hello,\n\n"
        "Your account has been created. Here are your login details:\n\n"
        f"Login URL: {login_url}\n"
        f"Email: {email}\n"
        f"Password: {password}\n\n"
        "Please change your password after your first login.\n\n"
        "Regards,\n"
        "HRMS Team\n"
    )
    return _send_plain_email(email, subject, body)
