import re
import random
import string

def generate_username_from_email(email):
    """Extract username from email"""
    # Example: aparnatulasi@gmail.com -> aparnatulasi
    username = email.split('@')[0]
    # Remove special characters
    username = re.sub(r'[^a-zA-Z0-9]', '', username)
    return username.lower()

def generate_company_code():
    """Generate random 4-digit company code"""
    return ''.join(random.choices(string.digits, k=4))

def generate_portal_url(username, company_code, subdomain, role):
    """Generate portal URL based on role"""
    if role == 'SUPER_ADMIN':
        return f"https://{username}.superadmin.com"
    elif role == 'ADMIN':
        # Format: https://usernameCompanyCode.company.com/role
        return f"https://{username}{company_code}.{subdomain}.com/{role.lower()}"
    elif role in ['HR', 'EMPLOYEE']:
        return f"https://{username}{company_code}.{subdomain}.com/{role.lower()}"
    else:
        return f"https://{subdomain}.com/{role.lower()}"