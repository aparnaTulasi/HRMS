ALLOWED_DOMAINS = [
    "tectoro.com", "tcs.com", "infosys.com", "wipro.com",
    "accenture.com", "capgemini.com", "hcl.com", "techmahindra.com", "gmail.com"
]

BLOCKED_DOMAINS = [
    "googlemail.com", "yahoo.com", "yahoo.in", "ymail.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "rediffmail.com", "rediff.com", "zoho.com", "protonmail.com",
    "gmx.com", "aol.com", "mail.com", "icloud.com", "me.com",
    "mac.com", "yandex.com", "fastmail.com", "tutanota.com",
    "inbox.com", "hushmail.com"
]

def validate_email(email):
    if not email or "@" not in email:
        return False, "Invalid email format"
    domain = email.split("@")[-1].lower()

    if domain in BLOCKED_DOMAINS:
        return False, "Public email domains are not allowed"
    if domain not in ALLOWED_DOMAINS:
        return False, "Company email required"
    return True, "Valid email"