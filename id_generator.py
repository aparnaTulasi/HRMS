from sqlalchemy import text

SYSTEM_PREFIX = "FS"  # for Super Admin IDs: FSSA01

def normalize_prefix(prefix: str) -> str:
    """
    Validates and normalizes the company prefix.
    Must be 2-4 uppercase letters.
    """
    p = (prefix or "").strip().upper()
    if not (2 <= len(p) <= 4) or not p.isalpha():
        raise ValueError("company_prefix must be 2 to 4 letters (A-Z)")
    return p

def next_company_user_uid(db, Company, company_id: int) -> str:
    """
    Generates the next User UID for a company safely using SQLite locking.
    Updates the company's last_user_number but does not commit.
    """
    # Locks SQLite for safe counter increment to prevent race conditions
    db.session.execute(text("BEGIN IMMEDIATE"))

    company = Company.query.get(company_id)
    if not company:
        raise ValueError("Company not found")

    if not company.company_prefix:
        raise ValueError("Company prefix not set")

    last = int(company.last_user_number or 0)
    next_num = last + 1
    company.last_user_number = next_num

    # Format: FS001, FS002 ... (3 digits)
    uid = f"{company.company_prefix}{next_num:03d}"
    return uid

def next_super_admin_uid(db) -> str:
    """
    Generates the next Super Admin UID using the global_counters table.
    """
    db.session.execute(text("BEGIN IMMEDIATE"))

    row = db.session.execute(
        text("SELECT value FROM global_counters WHERE key='SUPER_ADMIN'")
    ).fetchone()

    current = int(row[0]) if row else 0
    next_val = current + 1

    # Upsert logic safe for SQLite
    db.session.execute(text("INSERT OR IGNORE INTO global_counters(key,value) VALUES ('SUPER_ADMIN', 0)"))
    db.session.execute(text("UPDATE global_counters SET value=:v WHERE key='SUPER_ADMIN'"), {"v": next_val})

    # Format: FSSA01, FSSA02... (2 digits)
    return f"{SYSTEM_PREFIX}SA{next_val:02d}"