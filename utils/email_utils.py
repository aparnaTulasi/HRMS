import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from datetime import datetime


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
        msg["From"] = f"HRMS Team <{smtp_user}>"
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


def send_password_reset_otp(to_email: str, otp: str) -> bool:
    subject = "Password Reset OTP"
    body = f"Your password reset OTP is: {otp}\n\nValid for 10 minutes."
    return _send_plain_email(to_email, subject, body)


# --------------------------------
# Login Credentials Email (Admin/HR/Employee)
# --------------------------------
def send_account_created_alert(personal_email: str, company_name: str, created_by: str) -> bool:
    subject = "Account Created Alert"
    body = (
        "Hello,\n\n"
        f"An account was created for you in {company_name} by {created_by}.\n"
        f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
        f"Regards,\n"
        f"{company_name}\n"
    )
    return _send_plain_email(personal_email, subject, body)

def send_login_credentials(personal_email: str, company_email: str, password: str,
                           company_name: str, web_address: str, login_url: str, created_by: str) -> bool:
    subject = "Login Details"
    body = (
        "Hello,\n\n"
        f"Your account has been created by {created_by}.\n\n"
        "Login Details:\n"
        f"Web Address: {web_address}\n"
        f"Username: {company_email}\n"
        f"Password: {password}\n\n"
        "👉 Click here to login:\n"
        f"{login_url}\n\n"
        f"Regards,\n"
        f"{company_name}\n"
    )
    return _send_plain_email(personal_email, subject, body)

def send_login_success_email(to_email: str) -> bool:
    subject = "Login Successful"
    body = (
        "Hello,\n\n"
        "Login successful.\n"
        f"Date & Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Regards,\n"
        "Company Team\n"
    )
    return _send_plain_email(to_email, subject, body)
