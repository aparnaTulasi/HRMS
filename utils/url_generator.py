def clean_domain(domain: str) -> str:
    if not domain:
        return ""
    cleaned = domain.replace("http://", "").replace("https://", "").strip().strip("/")
    if cleaned and "." not in cleaned and cleaned != "localhost":
        return f"{cleaned}.com"
    return cleaned

def build_web_host(email: str, company) -> str:
    # example: jayadittakavi2004FIS001.test.com
    username = (email.split("@")[0] or "").strip().lower()
    code = (getattr(company, "company_code", "") or "").strip()
    domain = clean_domain(getattr(company, "subdomain", "") or "")
    return f"{username}{code}.{domain}"

def build_full_url(email: str, company) -> str:
    # API response lo http:// kavali
    return "http://" + build_web_host(email, company)