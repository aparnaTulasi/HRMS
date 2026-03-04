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

def build_company_base_url(subdomain):
    if subdomain:
        return f"http://{subdomain}.localhost:5000"
    return "http://localhost:5000"

def clean_domain(domain):
    if not domain:
        return ""
    return re.sub(r'[^a-z0-9]', '', domain.lower())

def build_web_address(subdomain):
    return build_company_base_url(subdomain)

def build_common_login_url():
    return build_company_base_url(None)