import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_login_credentials(to_email, password, login_url):
    """
    Sends an email to the new admin with their login credentials.
    """
    try:
        subject = "Your HRMS Admin Credentials"
        sender_email = current_app.config['MAIL_USERNAME']
        sender_password = current_app.config['MAIL_PASSWORD']
        smtp_server = current_app.config['MAIL_SERVER']
        smtp_port = current_app.config['MAIL_PORT']

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        body = f"""
        <h3>Welcome to HRMS</h3>
        <p>Your company account has been created successfully.</p>
        <p><strong>Login URL:</strong> <a href="{login_url}">{login_url}</a></p>
        <p><strong>Username:</strong> {to_email}</p>
        <p><strong>Password:</strong> {password}</p>
        <br>
        <p>Please login and change your password immediately.</p>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_otp_email(to_email, otp):
    """
    Sends an OTP to the user for verification.
    """
    try:
        subject = "Your HRMS Verification OTP"
        sender_email = current_app.config['MAIL_USERNAME']
        sender_password = current_app.config['MAIL_PASSWORD']
        smtp_server = current_app.config['MAIL_SERVER']
        smtp_port = current_app.config['MAIL_PORT']

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        body = f"""
        <h3>HRMS Verification</h3>
        <p>Your One Time Password (OTP) is:</p>
        <h2>{otp}</h2>
        <p>This OTP is valid for 10 minutes.</p>
        """
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False