from flask import current_app

def clean_domain(s: str) -> str:
    if not s:
        return ""
    return s.replace("http://", "").replace("https://", "").strip().strip("/")

ROOT_DOMAIN = "company.com"

def build_web_address(subdomain: str) -> str:
    sub = clean_domain(subdomain)
    if not sub:
        return "localhost:5173"
    return f"{sub}.{ROOT_DOMAIN}"

def build_common_login_url(subdomain: str) -> str:
    sub = clean_domain(subdomain)
    if not sub:
        return "http://localhost:5173/login"
    return f"https://{sub}.{ROOT_DOMAIN}/login"

def build_company_base_url(subdomain: str) -> str:
    sub = (subdomain or "").strip().lower()
    if not sub:
        return current_app.config.get("FRONTEND_LOCAL", "http://localhost:5173")

    protocol = current_app.config.get("FRONTEND_PROTOCOL", "https")
    base_domain = current_app.config.get("FRONTEND_BASE_DOMAIN", "company.com")
    return f"{protocol}://{sub}.{base_domain}"