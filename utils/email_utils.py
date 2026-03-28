import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# from flask import current_app (Moved inside function)
from datetime import datetime


def _send_plain_email(to_email: str, subject: str, body: str) -> bool:
    """
    Internal helper: sends email using SMTP config from Flask current_app.config
    """
    from flask import current_app
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
    body = (
        "Dear User,\n\n"
        "We received a request to create a Super Admin account for your HRMS.\n\n"
        f"Your One-Time Password (OTP) is: {otp}\n\n"
        "This OTP is valid for 10 minutes. Please do not share this code with anyone for security reasons.\n\n"
        "If you did not request this, please ignore this email or contact the HRMS support team immediately.\n\n"
        "Thank you,\n"
        "HRMS Team\n"
        "HR Management System\n"
        "support@hrms.com"
    )
    return _send_plain_email(to_email, subject, body)


def send_password_reset_otp(to_email: str, otp: str) -> bool:
    subject = "Password Reset OTP"
    body = (
        "Dear User,\n\n"
        "We received a request to reset your password for your HRMS account.\n\n"
        f"Your One-Time Password (OTP) is: {otp}\n\n"
        "This OTP is valid for 10 minutes. Please do not share this code with anyone for security reasons.\n\n"
        "If you did not request a password reset, please ignore this email or contact the HRMS support team immediately.\n\n"
        "Thank you,\n"
        "HRMS Team\n"
        "HR Management System\n"
        "support@hrms.com"
    )
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

def send_login_credentials(personal_email: str, company_email: str, 
                           company_name: str, web_address: str, reset_url: str, 
                           created_by: str, full_name: str = "User", password: str = None) -> bool:
    subject = "Login Details"
    body = (
        f"Hello,\n\n"
        f"Your account has been created by {created_by}.\n\n"
        f"Login Details:\n"
        f"Web Address: {web_address}\n"
        f"Username: {company_email}\n"
        f"Password: {password if password else 'Contact Admin'}\n\n"
        f"👉 Click here to login:\n"
        f"{web_address}\n\n"
        f"Regards,\n"
        f"{company_name.upper()}"
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
