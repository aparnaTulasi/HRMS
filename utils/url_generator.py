import re

def clean_username(email):
    if not email or '@' not in email:
        return "user"
    username = email.split('@')[0].lower()
    return re.sub(r'[^a-zA-Z0-9]', '', username)

def generate_login_url(email, role, company=None):
    username = clean_username(email)
    if role == 'SUPER_ADMIN':
        return f"https://{username}.superadmin.hrms.com"
    if company:
        return f"https://{company.subdomain}.hrms.com/{username}"
    return f"https://hrms.com/{username}"