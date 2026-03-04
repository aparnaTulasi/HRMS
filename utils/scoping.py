from flask import g
from utils.responses import fail

def get_company_id_for_request(requested_company_id=None):
    """
    SUPER_ADMIN can pass company_id.
    Others must always use their own company_id.
    """
    user = g.get('user')
    if not user:
        return None
        
    role = getattr(user, "role", None)
    my_company_id = getattr(user, "company_id", None)

    if role == "SUPER_ADMIN":
        return requested_company_id if requested_company_id is not None else my_company_id

    # non-superadmin: must have company_id
    if my_company_id is None:
        return None
    return my_company_id

def enforce_company_match(resource_company_id):
    """
    Ensure resource belongs to same company (except SUPER_ADMIN).
    Return None if allowed, else a JSON error response.
    """
    user = g.get('user')
    role = getattr(user, "role", None)
    if role == "SUPER_ADMIN":
        return None

    my_company_id = getattr(user, "company_id", None)
    if my_company_id is None or resource_company_id != my_company_id:
        return fail("Cross-company access blocked", 403)

    return None