def normalize_role(role: str) -> str:
    """
    Standardize role strings from common variations to canonical form.
    E.g., 'superadmin' or 'super-admin' -> 'SUPER_ADMIN'
    """
    if not role:
        return ""
    # Standardize format: hyphen to underscore, uppercase, and strip whitespace
    return role.replace("-", "_").upper().strip()
