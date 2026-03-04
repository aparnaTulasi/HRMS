from utils.responses import fail

def require_fields(data: dict, fields: list):
    missing = [f for f in fields if f not in data or data.get(f) in (None, "", [])]
    if missing:
        return fail("Validation failed", 400, errors={"missing_fields": missing})
    return None

def require_one_of(data: dict, fields: list):
    present = any(data.get(f) not in (None, "", []) for f in fields)
    if not present:
        return fail("Validation failed", 400, errors={"required_one_of": fields})
    return None