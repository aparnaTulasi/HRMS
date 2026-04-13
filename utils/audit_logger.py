from flask import request, g
from models import db
from models.audit_log import AuditLog
from datetime import datetime

def _get_module(entity):
    mapping = {
        'User': 'Auth',
        'AUTH': 'Auth',
        'Employee': 'Employee',
        'Attendance': 'Employee',
        'LeaveRequest': 'Employee',
        'Leave': 'Employee',
        'Shift': 'Employee',
        'Payroll': 'Finance',
        'Loan': 'Finance',
        'Payslip': 'Finance',
        'Company': 'Company',
        'Branch': 'Company',
        'Department': 'Company',
        'Designation': 'Company'
    }
    return mapping.get(entity, 'System')

def _generate_description(action, entity, meta=None):
    act = action.upper()
    ent = entity
    
    # Try to extract name from meta if available
    name = "Record"
    import json
    try:
        if meta:
            meta_dict = json.loads(meta.replace("'", '"')) if isinstance(meta, str) else meta
            name = meta_dict.get('name') or meta_dict.get('full_name') or meta_dict.get('company_name') or name
    except:
        pass

    if "LOGIN" in act: return f"Successful login"
    if "CREATE" in act: return f"Created new {ent}: {name}"
    if "UPDATE" in act: return f"Updated {ent} details for {name}"
    if "DELETE" in act: return f"Deleted {ent}: {name}"
    
    return f"Performed {act} on {ent}"

def log_action(action, entity, entity_id=None, status_code=200, meta=None, description=None, status=None, old_data=None, new_data=None):
    """
    Creates an audit log row with expanded metadata and time partitioning.
    """
    try:
        # Use g.user set by the token_required decorator
        user = g.get('user')
        now = datetime.utcnow()
        
        # Safe access to request properties
        method, path, remote_addr, user_agent = "N/A", "N/A", "0.0.0.0", "N/A"
        try:
            method = request.method
            path = request.path
            remote_addr = request.remote_addr
            user_agent = request.headers.get("User-Agent")
        except RuntimeError:
            pass

        # Use provided description or generate one
        final_desc = description or _generate_description(action, entity, meta)
        final_module = _get_module(entity)
        final_status = status or ("SUCCESS" if status_code < 400 else "FAILED")

        log = AuditLog(
            user_id=getattr(user, "id", None),
            user_name=getattr(user, "name", "System"),
            role=getattr(user, "role", "SYSTEM") if user else "SYSTEM",
            company_id=getattr(user, "company_id", None),

            module=final_module,
            action=action,
            description=final_desc,
            status=final_status,

            entity=entity,
            entity_id=entity_id,
            
            method=method,
            path=path,
            status_code=status_code,

            ip_address=remote_addr,
            user_agent=user_agent,
            meta=str(meta) if meta else None,
            old_data=old_data,
            new_data=new_data,

            created_at=now,
            year=now.year,
            month=now.month,
            day=now.day,
            hour=now.hour
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging action: {e}")
        db.session.rollback()

