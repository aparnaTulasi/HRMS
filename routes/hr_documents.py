# routes/hr_documents.py
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, date

from flask import Blueprint, request, jsonify, g, current_app, send_file
from werkzeug.utils import secure_filename

from models import db
from sqlalchemy import func
from utils.decorators import token_required, role_required

# NOTE: Make sure these models exist in models/hr_documents.py
from models.hr_documents import (
    OnboardingCandidate,
    LetterTemplate,
    LetterRequest,
    CertificateIssue,
    WFHRequest,
    HRDocument,
    LetterApprovalWorkflow,
    LetterApprovalWorkflowLevel,
    LetterApprovalStep,
    LetterVariable,
    EsignRequest,
    EsignSettings
)
from models.employee_documents import EmployeeDocument
from models.employee import Employee
from models.audit_log import AuditLog
from utils.audit_logger import log_action

hr_docs_bp = Blueprint("hr_docs_bp", __name__)

# =========================================================
# RBAC Helpers
# =========================================================
READ_ONLY_ROLES = {"ADMIN", "SUPER_ADMIN"}

def _company_id():
    return g.user.company_id

def _user_id():
    return g.user.id

def _is_read_only():
    return getattr(g.user, "role", None) in READ_ONLY_ROLES

def _hr_only():
    # HR can do everything
    if getattr(g.user, "role", None) != "HR":
        return jsonify({"success": False, "message": "Read-only access"}), 403
    return None

def _json_ok(data=None, message="OK"):
    return jsonify({"success": True, "message": message, "data": data})

def _render_template(body_html: str, context: dict) -> str:
    out = body_html or ""
    for k, v in (context or {}).items():
        out = out.replace("{{" + k + "}}", str(v))
    return out

def _save_text_as_file(content: str, file_prefix: str) -> str:
    """
    For now saving as .txt (works in download + email attachment).
    Later you can replace with real PDF generator.
    """
    folder = os.path.join(current_app.root_path, "uploads", "hr_docs")
    os.makedirs(folder, exist_ok=True)
    fname = f"{file_prefix}_{int(datetime.utcnow().timestamp())}.txt"
    path = os.path.join(folder, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def _send_email_with_attachment(to_email: str, subject: str, body: str, file_path: str) -> bool:
    smtp_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(current_app.config.get("MAIL_PORT", 587))
    smtp_user = current_app.config.get("MAIL_USERNAME")
    smtp_pass = current_app.config.get("MAIL_PASSWORD")

    if not smtp_user or not smtp_pass:
        print("❌ Mail credentials missing (MAIL_USERNAME / MAIL_PASSWORD).")
        return False

    if not file_path or not os.path.exists(file_path):
        print("❌ Attachment file not found:", file_path)
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = f"HRMS Team <{smtp_user}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with open(file_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
        msg.attach(part)

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=50)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        print(f"✅ Email sent to {to_email} with attachment")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


# =========================================================
# TAB 1: ONBOARDING (HR CRUD, Admin/SuperAdmin view only)
# =========================================================
@hr_docs_bp.get("/onboarding")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def onboarding_list():
    items = OnboardingCandidate.query.filter_by(company_id=_company_id()) \
        .order_by(OnboardingCandidate.updated_at.desc()).all()

    data = [{
        "id": x.id,
        "Candidate": x.candidate,
        "Role": x.role,
        "JoiningDate": x.joining_date.isoformat() if x.joining_date else None,
        "Status": x.status,
        "Progress": x.progress,
        "ReadOnly": _is_read_only()
    } for x in items]

    return _json_ok(data)


@hr_docs_bp.post("/onboarding")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def onboarding_create():
    err = _hr_only()
    if err: return err

    payload = request.get_json(silent=True) or {}
    if not payload.get("Candidate"):
        return jsonify({"success": False, "message": "Candidate is required"}), 400

    joining = payload.get("JoiningDate")
    joining_date = date.fromisoformat(joining) if joining else None

    obj = OnboardingCandidate(
        company_id=_company_id(),
        candidate=payload["Candidate"],
        role=payload.get("Role"),
        joining_date=joining_date,
        status=payload.get("Status", "IN_PROGRESS"),
        progress=int(payload.get("Progress", 0)),
        created_by=_user_id()
    )
    db.session.add(obj)
    db.session.commit()
    return _json_ok({"id": obj.id}, "Onboarding created")


@hr_docs_bp.put("/onboarding/<int:cid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def onboarding_update(cid):
    err = _hr_only()
    if err: return err

    obj = OnboardingCandidate.query.filter_by(id=cid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    payload = request.get_json(silent=True) or {}
    if "Candidate" in payload: obj.candidate = payload["Candidate"]
    if "Role" in payload: obj.role = payload["Role"]
    if "JoiningDate" in payload:
        obj.joining_date = date.fromisoformat(payload["JoiningDate"]) if payload["JoiningDate"] else None
    if "Status" in payload: obj.status = payload["Status"]
    if "Progress" in payload: obj.progress = int(payload["Progress"])

    db.session.commit()
    return _json_ok({"id": obj.id}, "Updated")


@hr_docs_bp.delete("/onboarding/<int:cid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def onboarding_delete(cid):
    err = _hr_only()
    if err: return err

    obj = OnboardingCandidate.query.filter_by(id=cid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    db.session.delete(obj)
    db.session.commit()
    return _json_ok({"id": cid}, "Deleted")


# =========================================================
# TAB 2: LETTERS
# HR: Generate + CRUD + Download + Email
# Admin/SuperAdmin: View only (no download)
# =========================================================
@hr_docs_bp.get("/letters/cards")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_cards():
    return _json_ok([
        {"letter_type": "OFFER", "title": "Offer Letter"},
        {"letter_type": "APPOINTMENT", "title": "Appointment Letter"},
        {"letter_type": "INCREMENT", "title": "Increment Letter"},
        {"letter_type": "RELIEVING", "title": "Relieving Letter"},
        {"letter_type": "PERFORMANCE", "title": "Performance Review Letter"},
    ])


@hr_docs_bp.get("/letters/templates/stats")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_template_stats():
    total = LetterTemplate.query.filter_by(company_id=_company_id(), is_active=True).count()
    active = LetterTemplate.query.filter_by(company_id=_company_id(), is_active=True, status="Active").count()
    draft = LetterTemplate.query.filter_by(company_id=_company_id(), is_active=True, status="Draft").count()
    
    # Sum of usage_count
    from sqlalchemy import func
    total_usage = db.session.query(func.sum(LetterTemplate.usage_count)).filter_by(company_id=_company_id(), is_active=True).scalar() or 0
    
    return _json_ok({
        "total_templates": total,
        "active_templates": active,
        "draft_templates": draft,
        "total_usage": total_usage
    })

@hr_docs_bp.get("/letters/templates/list")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_template_list():
    items = LetterTemplate.query.filter_by(company_id=_company_id(), is_active=True).all()
    data = [{
        "id": x.id,
        "template_name": x.title,
        "category": x.category,
        "last_modified": x.updated_at.strftime('%Y-%m-%d'),
        "status": x.status,
        "usage": x.usage_count,
        "resource_url": x.resource_url,
        "blog_link": x.blog_link
    } for x in items]
    return _json_ok(data)

@hr_docs_bp.get("/letters/templates/categories")
@token_required
def letters_template_categories():
    return _json_ok(["Recruitment", "Onboarding", "Performance", "Exit", "General"])

@hr_docs_bp.post("/letters/templates/add")
@token_required
@role_required(["HR"])
def letters_template_add():
    payload = request.get_json()
    if not payload.get("template_name") or not payload.get("content"):
        return jsonify({"success": False, "message": "Name and Content required"}), 400
        
    obj = LetterTemplate(
        company_id=_company_id(),
        letter_type=payload.get("category", "General").upper(), # Mapping category to letter_type for backward compat
        title=payload["template_name"],
        category=payload.get("category", "General"),
        body_html=payload["content"],
        resource_url=payload.get("resource_url"),
        blog_link=payload.get("blog_link"),
        status=payload.get("status", "Active"),
        created_by=_user_id()
    )
    db.session.add(obj)
    db.session.commit()
    return _json_ok({"id": obj.id}, "Template added")

@hr_docs_bp.put("/letters/templates/<int:tid>")
@token_required
@role_required(["HR"])
def letters_template_update(tid):
    obj = LetterTemplate.query.filter_by(id=tid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404
        
    payload = request.get_json()
    if "template_name" in payload: obj.title = payload["template_name"]
    if "category" in payload: 
        obj.category = payload["category"]
        obj.letter_type = payload["category"].upper()
    if "content" in payload: obj.body_html = payload["content"]
    if "resource_url" in payload: obj.resource_url = payload["resource_url"]
    if "blog_link" in payload: obj.blog_link = payload["blog_link"]
    if "status" in payload: obj.status = payload["status"]
    
    db.session.commit()
    return _json_ok({"id": obj.id}, "Template updated")

@hr_docs_bp.delete("/letters/templates/<int:tid>")
@token_required
@role_required(["HR"])
def letters_template_delete(tid):
    obj = LetterTemplate.query.filter_by(id=tid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404
        
    # Soft delete
    obj.is_active = False
    db.session.commit()
    return _json_ok({"id": tid}, "Template deleted")

@hr_docs_bp.post("/letters/templates/seed")


@hr_docs_bp.post("/letters/generate")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_generate():
    """
    UI body:
    {
      "LetterType":"OFFER",
      "EmployeeName":"Aparna",
      "EmployeeEmail":"aparna@gmail.com",
      "Date":"2026-02-11",
      "TemplateOption":"Standard Format",
      "SendEmailCopyToEmployee": true,
      "Extra": { "designation":"Dev", "ctc":"600000" }
    }
    """
    err = _hr_only()
    if err: return err

    payload = request.get_json(silent=True) or {}

    letter_type = payload.get("LetterType")
    employee_name = payload.get("EmployeeName")
    employee_email = payload.get("EmployeeEmail")
    letter_date_str = payload.get("Date")
    template_option = payload.get("TemplateOption", "Standard Format")
    send_copy = bool(payload.get("SendEmailCopyToEmployee", False))
    extra = payload.get("Extra") or {}

    if not letter_type or not employee_name or not employee_email or not letter_date_str:
        return jsonify({"success": False, "message": "LetterType, EmployeeName, EmployeeEmail, Date required"}), 400

    letter_type_str = str(letter_type)

    tmpl = LetterTemplate.query.filter_by(company_id=_company_id(), letter_type=letter_type, is_active=True).first()
    if not tmpl:
        return jsonify({"success": False, "message": "No active template for this LetterType"}), 400

    # dynamic context
    context = {
        "employee_name": employee_name,
        "employee_email": employee_email,
        "date": letter_date_str,
        "template_option": template_option,
        "company_name": getattr(g.user, "company_name", "") or "Company",
        **extra
    }

    # Create DB record first
    req = LetterRequest(
        company_id=_company_id(),
        letter_type=letter_type,
        template_id=tmpl.id,
        employee_name=employee_name,
        employee_email=employee_email,
        letter_date=date.fromisoformat(str(letter_date_str)),
        template_option=template_option,
        send_email_copy=send_copy,
        payload=context,
        current_version=1,
        created_by=_user_id()
    )
    db.session.add(req)
    db.session.flush()

    # Check for Approval Workflow
    workflow = LetterApprovalWorkflow.query.filter_by(
        company_id=_company_id(), 
        letter_type=letter_type, 
        is_active=True, 
        status="Active"
    ).first()
    
    if workflow:
        req.status = "IN_REVIEW"
        # Create approval steps
        for level in sorted(workflow.levels, key=lambda x: x.step_no):
            step = LetterApprovalStep(
                request_id=req.id,
                step_no=level.step_no,
                approver_role=level.role,
                status="PENDING" if level.step_no == 1 else "AWAITING_PREVIOUS"
            )
            db.session.add(step)
    else:
        req.status = "GENERATED"

    # Generate file
    rendered = _render_template(tmpl.body_html, context)
    file_path = _save_text_as_file(rendered, f"letter_{letter_type_str.lower()}_{req.id}_v1")
    req.pdf_path = file_path

    # Send email only if already approved or no workflow
    email_status = "Not Sent (Awaiting Approval)" if workflow else "Not Sent"
    if not workflow and send_copy:
        subject = f"{tmpl.title} - {employee_name}"
        body = f"Hello {employee_name},\n\nPlease find attached your {tmpl.title}.\nDate: {letter_date_str}\n\nRegards,\nHR Team"
        sent = _send_email_with_attachment(str(employee_email), subject, body, file_path)
        if sent:
            req.status = "SENT"
            email_status = "Sent"
        else:
            req.status = "FAILED"
            email_status = "Failed"

    db.session.commit()

    # IMPORTANT: give absolute URL too (helps frontend)
    abs_download = request.host_url.rstrip("/") + f"/api/hr-docs/letters/request/{req.id}/download"

    return _json_ok({
        "RequestId": req.id,
        "LetterType": letter_type,
        "EmployeeName": employee_name,
        "EmployeeEmail": employee_email,
        "Date": letter_date_str,
        "TemplateOption": template_option,
        "Status": req.status,
        "EmailStatus": email_status,
        "DownloadUrl": f"/api/hr-docs/letters/request/{req.id}/download",
        "DownloadUrlAbsolute": abs_download
    }, "Letter generated")


# =========================================================
# TAB 3: APPROVALS
# =========================================================
@hr_docs_bp.get("/letters/approval/stats")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_approval_stats():
    pending = LetterApprovalStep.query.filter_by(status="PENDING").count()
    active_workflows = LetterApprovalWorkflow.query.filter_by(company_id=_company_id(), is_active=True, status="Active").count()
    
    # Simple count for this month
    current_month = datetime.utcnow().month
    approved_this_month = LetterApprovalStep.query.filter(
        LetterApprovalStep.status == "APPROVED",
        db.func.extract('month', LetterApprovalStep.action_at) == current_month
    ).count()
    rejected = LetterApprovalStep.query.filter_by(status="REJECTED").count()
    
    return _json_ok({
        "pending_approvals": pending,
        "active_workflows": active_workflows,
        "approved_this_month": approved_this_month,
        "rejected": rejected
    })

@hr_docs_bp.get("/letters/approval/pending")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN", "MANAGER"])
def letters_approval_pending():
    # Filter by user's role or specific user_id
    # For now, show all pending for simplicity or filter by role
    user_role = g.user.role
    steps = LetterApprovalStep.query.filter_by(status="PENDING", approver_role=user_role).all()
    
    data = []
    for s in steps:
        req = LetterRequest.query.get(s.request_id)
        if not req or req.company_id != _company_id(): continue
        
        # Calculate level progress
        total_steps = LetterApprovalStep.query.filter_by(request_id=req.id).count()
        current_level_no = s.step_no
        
        data.append({
            "id": s.id,
            "letter_id": f"L{req.id:03}",
            "employee": req.employee_name,
            "letter_type": req.letter_type,
            "requested_by": "HR", # Should be from req.created_by
            "date": req.letter_date.isoformat() if req.letter_date else None,
            "approval_level": f"Level {current_level_no}/{total_steps}",
            "request_id": req.id
        })
    return _json_ok(data)

@hr_docs_bp.post("/letters/approval/<int:step_id>/action")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN", "MANAGER"])
def letters_approval_action(step_id):
    step = LetterApprovalStep.query.get_or_404(step_id)
    payload = request.get_json()
    action = payload.get("action") # APPROVE, REJECT
    comments = payload.get("comments")
    
    if action not in ["APPROVE", "REJECT"]:
        return jsonify({"success": False, "message": "Invalid action"}), 400
        
    step.status = "APPROVED" if action == "APPROVE" else "REJECTED"
    step.action_by = _user_id()
    step.action_at = datetime.utcnow()
    step.comments = comments
    
    req = LetterRequest.query.get(step.request_id)
    
    if action == "APPROVE":
        # Check if there's a next step
        next_step = LetterApprovalStep.query.filter_by(
            request_id=step.request_id, 
            step_no=step.step_no + 1
        ).first()
        if not next_step:
            req.status = "APPROVED"
        else:
            next_step.status = "PENDING"
    else:
        req.status = "REJECTED"
        # Optional: set all subsequent steps to REJECTED or CANCELLED
        LetterApprovalStep.query.filter(
            LetterApprovalStep.request_id == step.request_id,
            LetterApprovalStep.step_no > step.step_no
        ).update({"status": "REJECTED"})
        
    db.session.commit()
    return _json_ok({"status": step.status}, f"Letter {action.lower()}d")

# Workflow CRUD
@hr_docs_bp.get("/letters/approval/workflows")
@token_required
@role_required(["HR"])
def letters_workflow_list():
    workflows = LetterApprovalWorkflow.query.filter_by(company_id=_company_id(), is_active=True).all()
    data = []
    for w in workflows:
        levels = [{"level": l.step_no, "role": l.role} for l in sorted(w.levels, key=lambda x: x.step_no)]
        data.append({
            "id": w.id,
            "name": w.name,
            "letter_type": w.letter_type,
            "status": w.status,
            "levels": levels
        })
    return _json_ok(data)

@hr_docs_bp.post("/letters/approval/workflows")
@token_required
@role_required(["HR"])
def letters_workflow_add():
    payload = request.get_json()
    if not payload.get("name") or not payload.get("letter_type"):
        return jsonify({"success": False, "message": "Name and Letter Type required"}), 400
        
    w = LetterApprovalWorkflow(
        company_id=_company_id(),
        name=payload["name"],
        letter_type=payload["letter_type"],
        status=payload.get("status", "Active"),
        created_by=_user_id()
    )
    db.session.add(w)
    db.session.commit()
    return _json_ok({"id": w.id}, "Workflow created")

@hr_docs_bp.post("/letters/approval/workflows/<int:wid>/levels")
@token_required
@role_required(["HR"])
def letters_workflow_add_level(wid):
    w = LetterApprovalWorkflow.query.filter_by(id=wid, company_id=_company_id()).first_or_404()
    payload = request.get_json()
    
    level = LetterApprovalWorkflowLevel(
        workflow_id=w.id,
        step_no=payload["step_no"],
        role=payload["role"],
        user_id=payload.get("user_id")
    )
    db.session.add(level)
    db.session.commit()
    return _json_ok({"id": level.id}, "Level added")

# =========================================================
# TAB: E-SIGN
# =========================================================
@hr_docs_bp.get("/esign/summary")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def esign_summary():
    total_sent = EsignRequest.query.filter_by(company_id=_company_id()).count()
    signed = EsignRequest.query.filter_by(company_id=_company_id(), status="Signed").count()
    pending = EsignRequest.query.filter_by(company_id=_company_id(), status="Pending").count()
    overdue = EsignRequest.query.filter_by(company_id=_company_id(), status="Overdue").count()
    
    return _json_ok({
        "total_sent": total_sent,
        "signed": signed,
        "pending": pending,
        "overdue": overdue
    })

@hr_docs_bp.get("/esign/requests")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def esign_requests():
    status_filter = request.args.get("status")
    query = EsignRequest.query.filter_by(company_id=_company_id())
    
    if status_filter and status_filter != "All Status":
        query = query.filter_by(status=status_filter)
        
    items = query.order_by(EsignRequest.sent_date.desc()).all()
    
    data = []
    for x in items:
        data.append({
            "id": f"ES-{x.id:03}",
            "employee": x.employee.full_name if x.employee else "Unknown",
            "letter_type": x.letter_type,
            "sent_date": x.sent_date.isoformat() if x.sent_date else None,
            "due_date": x.due_date.isoformat() if x.due_date else None,
            "status": x.status,
            "request_id": x.request_id
        })
    return _json_ok(data)

@hr_docs_bp.post("/esign/requests")
@token_required
@role_required(["HR"])
def esign_request_create():
    payload = request.get_json()
    emp_name_or_id = payload.get("employee") # Search was done on frontend or via search helper
    letter_type = payload.get("letter_type")
    deadline_str = payload.get("deadline")
    
    if not letter_type or not deadline_str:
        return jsonify({"success": False, "message": "Letter Type and Deadline required"}), 400
        
    # Find employee
    employee = None
    if payload.get("employee_id"):
        employee = Employee.query.get(payload["employee_id"])
    
    if not employee:
        return jsonify({"success": False, "message": "Employee not found"}), 404
        
    req = EsignRequest(
        company_id=_company_id(),
        employee_id=employee.id,
        letter_type=letter_type,
        due_date=date.fromisoformat(deadline_str),
        status="Pending",
        created_by=_user_id()
    )
    db.session.add(req)
    db.session.commit()
    return _json_ok({"id": req.id}, "E-Sign request sent")

@hr_docs_bp.get("/esign/settings")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def esign_settings_get():
    s = EsignSettings.query.filter_by(company_id=_company_id()).first()
    if not s:
        # Default settings if none exist
        s = EsignSettings(company_id=_company_id())
        db.session.add(s)
        db.session.commit()
        
    return _json_ok({
        "otp_enabled": s.otp_enabled,
        "selfie_enabled": s.selfie_enabled,
        "aadhaar_enabled": s.aadhaar_enabled,
        "reminders_enabled": s.reminders_enabled
    })

@hr_docs_bp.put("/esign/settings")
@token_required
@role_required(["HR"])
def esign_settings_update():
    payload = request.get_json()
    s = EsignSettings.query.filter_by(company_id=_company_id()).first()
    if not s:
        s = EsignSettings(company_id=_company_id())
        db.session.add(s)
        
    if "otp_enabled" in payload: s.otp_enabled = bool(payload["otp_enabled"])
    if "selfie_enabled" in payload: s.selfie_enabled = bool(payload["selfie_enabled"])
    if "aadhaar_enabled" in payload: s.aadhaar_enabled = bool(payload["aadhaar_enabled"])
    if "reminders_enabled" in payload: s.reminders_enabled = bool(payload["reminders_enabled"])
    
    db.session.commit()
    return _json_ok(None, "Settings updated")

@hr_docs_bp.post("/esign/requests/<int:rid>/resend")
@token_required
@role_required(["HR"])
def esign_request_resend(rid):
    req = EsignRequest.query.filter_by(id=rid, company_id=_company_id()).first()
    if not req:
        return jsonify({"success": False, "message": "Request not found"}), 404
        
    req.sent_date = date.today()
    req.status = "Pending"
    db.session.commit()
    return _json_ok(None, "E-Sign request resent")

@hr_docs_bp.get("/esign/requests/<int:rid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def esign_request_get(rid):
    x = EsignRequest.query.filter_by(id=rid, company_id=_company_id()).first()
    if not x:
        return jsonify({"success": False, "message": "Not found"}), 404
        
    return _json_ok({
        "id": f"ES-{x.id:03}",
        "employee": x.employee.full_name if x.employee else "Unknown",
        "letter_type": x.letter_type,
        "sent_date": x.sent_date.isoformat() if x.sent_date else None,
        "due_date": x.due_date.isoformat() if x.due_date else None,
        "status": x.status,
        "request_id": x.request_id
    })

# =========================================================
# TAB 2: VARIABLES
# =========================================================
@hr_docs_bp.get("/letters/variables/list")
@token_required
def letters_variable_list():
    items = LetterVariable.query.filter_by(company_id=_company_id(), is_active=True).all()
    data = [{
        "id": x.id,
        "name": x.name,
        "description": x.description,
        "source": x.source
    } for x in items]
    return _json_ok(data)

@hr_docs_bp.post("/letters/variables/add")
@token_required
@role_required(["HR"])
def letters_variable_add():
    payload = request.get_json()
    if not payload.get("name"):
        return jsonify({"success": False, "message": "Variable name required"}), 400
        
    v = LetterVariable(
        company_id=_company_id(),
        name=payload["name"],
        description=payload.get("description"),
        source="Custom",
        is_active=True
    )
    db.session.add(v)
    db.session.commit()
    return _json_ok({"id": v.id}, "Variable added")

@hr_docs_bp.delete("/letters/variables/<int:vid>")
@token_required
@role_required(["HR"])
def letters_variable_delete(vid):
    v = LetterVariable.query.filter_by(id=vid, company_id=_company_id()).first_or_404()
    if v.source == "System":
        return jsonify({"success": False, "message": "Cannot delete system variables"}), 403
        
    v.is_active = False
    db.session.commit()
    return _json_ok({"id": vid}, "Variable deleted")

@hr_docs_bp.post("/letters/variables/seed")
@token_required
@role_required(["HR"])
def letters_variable_seed():
    defaults = [
        ("employee_name", "Full Name of the Employee"),
        ("designation", "Job Title / Designation"),
        ("joining_date", "Date of joining"),
        ("ctc", "Annual CTC amount"),
        ("company_name", "Name of the Company"),
        ("department", "Department name"),
        ("effective_date", "The date from which changes apply"),
        ("last_working_day", "The last day of employment")
    ]
    
    created = 0
    for name, desc in defaults:
        exists = LetterVariable.query.filter_by(company_id=_company_id(), name=name, is_active=True).first()
        if not exists:
            db.session.add(LetterVariable(
                company_id=_company_id(),
                name=name,
                description=desc,
                source="System"
            ))
            created += 1
    db.session.commit()
    return _json_ok({"created": created}, "System variables seeded")

# =========================================================
# DOCUMENTS CENTER
# =========================================================

# TAB 1: COMPANY POLICIES
@hr_docs_bp.get("/policies/list")
@token_required
def policies_list():
    """
    Unified view:
    - Admin/SA/HR see all policies.
    - Employees see only active and non-sensitive policies.
    """
    q = HRDocument.query
    if g.user.role not in ['SUPER_ADMIN']:
        q = q.filter_by(company_id=_company_id())
    
    if g.user.role in ['EMPLOYEE', 'MANAGER']:
        q = q.filter_by(is_active=True, is_sensitive=False)
        
    items = q.order_by(HRDocument.created_at.desc()).all()
    data = [{
        "id": x.id,
        "document_name": x.title,
        "category": x.category,
        "type": x.file_type or "PDF",
        "size": x.file_size or "0.0 MB",
        "upload_date": x.created_at.strftime('%b %d, %Y'),
        "status": x.status,
        "is_active": x.is_active,
        "is_sensitive": x.is_sensitive,
        "views": x.view_count or 0
    } for x in items]
    return _json_ok(data)

@hr_docs_bp.post("/policies/upload")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def policies_upload():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    file = request.files['file']
    title = request.form.get("title")
    category = request.form.get("category", "Policy")
    
    if not file or not title:
        return jsonify({"success": False, "message": "File and Title required"}), 400
        
    filename = secure_filename(file.filename)
    # Ensure uploads directory exists
    upload_dir = os.path.join(current_app.root_path, 'uploads', 'policies')
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{datetime.utcnow().timestamp()}_{filename}")
    file.save(file_path)
    
    # Calculate size
    size_bytes = os.path.getsize(file_path)
    size_str = f"{size_bytes / (1024*1024):.1f} MB" if size_bytes > 1024*1024 else f"{size_bytes / 1024:.1f} KB"
    ext = filename.split('.')[-1].upper() if '.' in filename else 'FILE'

    obj = HRDocument(
        company_id=_company_id(),
        title=title,
        category=category,
        file_path=file_path,
        file_size=size_str,
        file_type=ext,
        created_by=_user_id()
    )
    db.session.add(obj)
    db.session.commit()
    return _json_ok({"id": obj.id}, "Policy uploaded")

@hr_docs_bp.delete("/policies/<int:pid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def policies_delete(pid):
    obj = HRDocument.query.filter_by(id=pid, company_id=_company_id()).first_or_404()
    # Optional: Delete file from disk
    if os.path.exists(obj.file_path):
        os.remove(obj.file_path)
    db.session.delete(obj)
    db.session.commit()
    return _json_ok({"id": pid}, "Policy deleted")

@hr_docs_bp.get("/policies/<int:pid>/download")
@token_required
def policies_download(pid):
    obj = HRDocument.query.filter_by(id=pid).first_or_404()
    if g.user.role not in ['SUPER_ADMIN'] and obj.company_id != _company_id():
        return jsonify({"success": False, "message": "Access denied"}), 403
    
    # Restrict sensitive docs to Admin/SA
    if obj.is_sensitive and g.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return jsonify({"success": False, "message": "Sensitive document access denied"}), 403

    if not os.path.exists(obj.file_path):
        return jsonify({"success": False, "message": "File not found on server"}), 404
        
    # Audit trail for preparation/viewing
    log_action("DOCUMENT_VIEW", "HRDocument", obj.id, 200, meta={"title": obj.title, "employee": g.user.email})
    obj.view_count = (obj.view_count or 0) + 1
    obj.last_viewed_at = datetime.utcnow()
    db.session.commit()

    return send_file(obj.file_path, as_attachment=True, download_name=os.path.basename(obj.file_path))

# TAB 2: EMPLOYEE DOCUMENTS
@hr_docs_bp.get("/employee-docs/list")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def employee_docs_list():
    search = request.args.get("search", "")
    query = db.session.query(EmployeeDocument, Employee).join(Employee, EmployeeDocument.employee_id == Employee.id)
    query = query.filter(Employee.company_id == _company_id())
    
    if search:
        query = query.filter(Employee.full_name.ilike(f"%{search}%"))
        
    items = query.all()
    data = []
    for doc, emp in items:
        # Calculate size if not stored
        size_str = "0.0 MB"
        if doc.file_path and os.path.exists(doc.file_path):
            size_bytes = os.path.getsize(doc.file_path)
            size_str = f"{size_bytes / (1024*1024):.1f} MB" if size_bytes > 1024*1024 else f"{size_bytes / 1024:.1f} KB"

        data.append({
            "id": doc.id,
            "employee_name": emp.full_name,
            "document_name": doc.document_name or doc.document_type,
            "type": doc.file_path.split('.')[-1].upper() if doc.file_path and '.' in doc.file_path else 'PDF',
            "verification_status": "Verified" if doc.verified else "Pending Verification",
            "size": size_str,
            "upload_date": doc.created_at.strftime('%b %d, %Y')
        })
    return _json_ok(data)

@hr_docs_bp.post("/employee-docs/<int:did>/verify")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def employee_docs_verify(did):
    doc = EmployeeDocument.query.get_or_404(did)
    # Check company ownership
    emp = Employee.query.get(doc.employee_id)
    if not emp or emp.company_id != _company_id():
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    doc.verified = not doc.verified # Toggle
    doc.verified_by = _user_id()
    doc.verified_date = datetime.utcnow()
    db.session.commit()
    return _json_ok({"verified": doc.verified}, "Status updated")

@hr_docs_bp.get("/employee-docs/<int:did>/download")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def employee_docs_download(did):
    doc = EmployeeDocument.query.get_or_404(did)
    emp = Employee.query.get(doc.employee_id)
    if not emp or emp.company_id != _company_id():
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    if not doc.file_path or not os.path.exists(doc.file_path):
        return jsonify({"success": False, "message": "File not found"}), 404
    return send_file(doc.file_path, as_attachment=True)

# EMPLOYEE VIEW
@hr_docs_bp.get("/employee/policies")
@token_required
def employee_policies():
    # Employees can see all policies for their company
    items = HRDocument.query.filter_by(company_id=_company_id()).all()
    data = [{
        "id": x.id,
        "document_name": x.title,
        "category": x.category,
        "type": x.file_type or "PDF",
        "size": x.file_size or "0.0 MB",
        "upload_date": x.created_at.strftime('%b %d, %Y')
    } for x in items]
    return _json_ok(data)

@hr_docs_bp.get("/letters/recent")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_recent():
    items = LetterRequest.query.filter_by(company_id=_company_id()).order_by(LetterRequest.created_at.desc()).all()
    data = [{
        "RequestId": x.id,
        "Employee": x.employee_name,
        "LetterType": x.letter_type,
        "Status": x.status,
        "Date": x.letter_date.isoformat() if x.letter_date else None,
        "ReadOnly": _is_read_only(),
        "CanDownload": (g.user.role == "HR")
    } for x in items]
    return _json_ok(data)


@hr_docs_bp.get("/letters/request/<int:rid>/view")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_view(rid):
    req = LetterRequest.query.filter_by(id=rid, company_id=_company_id()).first()
    if not req:
        return jsonify({"success": False, "message": "Not found"}), 404

    tmpl = LetterTemplate.query.filter_by(id=req.template_id, company_id=_company_id()).first()
    preview_html = _render_template(tmpl.body_html, req.payload or {}) if tmpl else ""

    return _json_ok({
        "RequestId": req.id,
        "LetterType": req.letter_type,
        "Status": req.status,
        "EmployeeName": req.employee_name,
        "EmployeeEmail": req.employee_email,
        "Date": req.letter_date.isoformat() if req.letter_date else None,
        "TemplateOption": req.template_option,
        "PreviewHtml": preview_html,
        "ReadOnly": _is_read_only(),
        "CanDownload": (g.user.role == "HR")
    })


@hr_docs_bp.put("/letters/request/<int:rid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_update(rid):
    err = _hr_only()
    if err: return err

    req = LetterRequest.query.filter_by(id=rid, company_id=_company_id()).first()
    if not req:
        return jsonify({"success": False, "message": "Not found"}), 404

    payload = request.get_json(silent=True) or {}

    # allowed edits
    if "EmployeeName" in payload: req.employee_name = payload["EmployeeName"]
    if "EmployeeEmail" in payload: req.employee_email = payload["EmployeeEmail"]
    if "Date" in payload and payload["Date"]:
        req.letter_date = date.fromisoformat(payload["Date"])
        # keep in payload too if exists
        if req.payload: req.payload["date"] = payload["Date"]

    if "TemplateOption" in payload: req.template_option = payload["TemplateOption"]
    if "SendEmailCopyToEmployee" in payload: req.send_email_copy = bool(payload["SendEmailCopyToEmployee"])
    if "Extra" in payload and isinstance(payload["Extra"], dict):
        if not req.payload: req.payload = {}
        req.payload.update(payload["Extra"])

    db.session.commit()
    return _json_ok({"RequestId": req.id}, "Updated")


@hr_docs_bp.delete("/letters/request/<int:rid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_delete(rid):
    err = _hr_only()
    if err: return err

    req = LetterRequest.query.filter_by(id=rid, company_id=_company_id()).first()
    if not req:
        return jsonify({"success": False, "message": "Not found"}), 404

    db.session.delete(req)
    db.session.commit()
    return _json_ok({"RequestId": rid}, "Deleted")


@hr_docs_bp.get("/letters/request/<int:rid>/download")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_download(rid):
    # STRICT: only HR can download
    err = _hr_only()
    if err: return err

    req = LetterRequest.query.filter_by(id=rid, company_id=_company_id()).first()
    if not req or not req.pdf_path:
        return jsonify({"success": False, "message": "File not found"}), 404

    # if file missing, regenerate (safe)
    if not os.path.exists(req.pdf_path):
        tmpl = LetterTemplate.query.filter_by(id=req.template_id, company_id=_company_id()).first()
        if tmpl:
            rendered = _render_template(tmpl.body_html, req.payload or {})
            req.pdf_path = _save_text_as_file(rendered, f"letter_{req.letter_type.lower()}_{req.id}_v{req.current_version or 1}")
            db.session.commit()

    if not req.pdf_path or not os.path.exists(req.pdf_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    return send_file(req.pdf_path, as_attachment=True)


# =========================================================
# TAB 3: CERTIFICATES (3 types)
# HR CRUD + download + email
# Admin/SuperAdmin view only, no download
# =========================================================
@hr_docs_bp.post("/certificates/issue")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_issue():
    """
    UI body:
    {
      "CertificateType":"EXPERIENCE_CERTIFICATE" | "NOC_LETTER" | "INTERNSHIP_CERTIFICATE",
      "Recipient":"Mark Wilson",
      "RecipientEmail":"mark@gmail.com",
      "Date":"2026-02-11",
      "TemplateOption":"Standard Format",
      "SendEmailCopyToEmployee": true,
      "Details": { ... }
    }
    """
    err = _hr_only()
    if err: return err

    payload = request.get_json(silent=True) or {}

    cert_type = payload.get("CertificateType")
    recipient = payload.get("Recipient") 
    employee_id_str = payload.get("EmployeeID")
    designation = payload.get("Designation")
    issue_date_str = payload.get("Date")
    purpose = payload.get("Purpose")
    
    template_option = payload.get("TemplateOption", "Standard Format")
    send_copy = bool(payload.get("SendEmailCopyToEmployee", False))

    if not cert_type or not recipient or not issue_date_str:
        return jsonify({"success": False, "message": "CertificateType, Recipient (Name), and Date are required"}), 400

    # Ensure cert_type is safe for lower()
    cert_type_safe = str(cert_type).lower()

    # Store designation and purpose in payload
    context = {
        "recipient": recipient,
        "employee_id": employee_id_str,
        "designation": designation,
        "purpose": purpose,
        "date": issue_date_str,
        "template_option": template_option
    }

    # Simplified content for generation
    description_map = {
        "EXPERIENCE_CERTIFICATE": "Experience Certificate",
        "INTERNSHIP_CERTIFICATE": "Internship Certificate",
        "APPRECIATION_LETTER": "Appreciation Letter"
    }
    cert_title = description_map.get(cert_type, cert_type.replace('_', ' ').title())

    content = f"{cert_title}\n\n"
    content += f"This is to certify that {recipient} ({employee_id_str or 'N/A'}) "
    if designation:
        content += f"has worked as {designation}. "
    if purpose:
        content += f"\n\nPurpose/Remarks: {purpose}"
    content += f"\n\nIssued Date: {issue_date_str}"

    file_path = _save_text_as_file(content, f"certificate_{cert_type_safe}")

    obj = CertificateIssue(
        company_id=_company_id(),
        recipient=recipient,
        certificate_type=cert_type,
        issue_date=date.fromisoformat(str(issue_date_str)),
        template_option=template_option,
        send_email_copy=send_copy,
        payload=context, # Stores designation, purpose, etc.
        pdf_path=file_path,
        issued_by=_user_id()
    )
    db.session.add(obj)
    db.session.commit()

    return _json_ok({
        "CertificateId": obj.id,
        "Recipient": recipient,
        "CertificateType": cert_type,
        "IssueDate": issue_date_str
    }, "Certificate issued")


@hr_docs_bp.get("/certificates/history")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_history():
    items = CertificateIssue.query.filter_by(company_id=_company_id()) \
        .order_by(CertificateIssue.created_at.desc()).all()

    data = []
    for x in items:
        # Get details from payload if needed
        payload = x.payload or {}
        data.append({
            "id": x.id,
            "Recipient": x.recipient,
            "EmployeeID": payload.get("employee_id", "N/A"),
            "CertificateType": x.certificate_type.replace('_', ' ').title(),
            "IssueDate": x.issue_date.strftime('%b %d, %Y') if x.issue_date else "N/A",
            "Actions": {
                "view": True,
                "download": bool(x.pdf_path)
            }
        })
    return _json_ok(data)


@hr_docs_bp.get("/certificates/<int:cid>/view")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_view(cid):
    obj = CertificateIssue.query.filter_by(id=cid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    return _json_ok({
        "id": obj.id,
        "Recipient": obj.recipient,
        "CertificateType": obj.certificate_type,
        "IssueDate": obj.issue_date.isoformat() if obj.issue_date else None,
        "Payload": obj.payload, # Contains EmployeeID, Designation, Purpose
        "ReadOnly": _is_read_only()
    })

@hr_docs_bp.get("/onboarding/employees/search")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def onboarding_employee_search():
    """
    Helper for Certificate Modal to search employees by name.
    """
    search_query = request.args.get("q", "")
    if not search_query:
        return _json_ok([])
        
    employees = Employee.query.filter(
        Employee.company_id == _company_id(),
        Employee.full_name.ilike(f"%{search_query}%")
    ).limit(10).all()
    
    data = [{
        "id": e.id,
        "full_name": e.full_name,
        "employee_id_code": e.employee_id_code, # e.g. EMP-101
        "designation": e.designation
    } for e in employees]
    
    return _json_ok(data)


@hr_docs_bp.put("/certificates/<int:cid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_update(cid):
    err = _hr_only()
    if err: return err

    obj = CertificateIssue.query.filter_by(id=cid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    payload = request.get_json(silent=True) or {}

    if "Recipient" in payload: obj.recipient = payload["Recipient"]
    if "RecipientEmail" in payload: obj.recipient_email = payload["RecipientEmail"]
    if "Date" in payload and payload["Date"]:
        obj.issue_date = date.fromisoformat(payload["Date"])
    if "TemplateOption" in payload: obj.template_option = payload["TemplateOption"]
    if "SendEmailCopyToEmployee" in payload: obj.send_email_copy = bool(payload["SendEmailCopyToEmployee"])
    if "Details" in payload and isinstance(payload["Details"], dict):
        if not obj.payload: obj.payload = {}
        obj.payload.update(payload["Details"])

    db.session.commit()
    return _json_ok({"CertificateId": obj.id}, "Updated")


@hr_docs_bp.delete("/certificates/<int:cid>")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_delete(cid):
    err = _hr_only()
    if err: return err

    obj = CertificateIssue.query.filter_by(id=cid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    db.session.delete(obj)
    db.session.commit()
    return _json_ok({"CertificateId": cid}, "Deleted")


@hr_docs_bp.get("/certificates/<int:cid>/download")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_download(cid):
    # STRICT: only HR can download
    err = _hr_only()
    if err: return err

    obj = CertificateIssue.query.filter_by(id=cid, company_id=_company_id()).first()
    if not obj or not obj.pdf_path:
        return jsonify({"success": False, "message": "File not found"}), 404

    # regenerate if missing
    if not os.path.exists(obj.pdf_path):
        content = f"{obj.certificate_type}\nRecipient: {obj.recipient}\nDate: {obj.issue_date.isoformat() if obj.issue_date else ''}\n"
        obj.pdf_path = _save_text_as_file(content, f"certificate_{obj.certificate_type.lower()}_{obj.id}")
        db.session.commit()

    if not obj.pdf_path or not os.path.exists(obj.pdf_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    return send_file(obj.pdf_path, as_attachment=True)


# =========================================================
# TAB 4: WFH (HR CRUD, Admin/SuperAdmin view only)
# =========================================================
@hr_docs_bp.get("/wfh")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def wfh_list():
    items = WFHRequest.query.filter_by(company_id=_company_id()) \
        .order_by(WFHRequest.created_at.desc()).all()

    data = [{
        "id": x.id,
        "Employee": x.employee,
        "Duration": f"{x.from_date.isoformat()} to {x.to_date.isoformat()}",
        "Reason": x.reason,
        "Status": x.status,
        "ReadOnly": _is_read_only()
    } for x in items]
    return _json_ok(data)


@hr_docs_bp.post("/wfh")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def wfh_create():
    err = _hr_only()
    if err: return err

    payload = request.get_json(silent=True) or {}
    if not payload.get("Employee") or not payload.get("FromDate") or not payload.get("ToDate"):
        return jsonify({"success": False, "message": "Employee, FromDate, ToDate required"}), 400

    obj = WFHRequest(
        company_id=_company_id(),
        employee=payload["Employee"],
        employee_id=payload.get("employee_id"),
        from_date=date.fromisoformat(payload["FromDate"]),
        to_date=date.fromisoformat(payload["ToDate"]),
        reason=payload.get("Reason"),
        status="PENDING",
        created_by=_user_id()
    )
    db.session.add(obj)
    db.session.commit()
    return _json_ok({"id": obj.id}, "WFH created")


@hr_docs_bp.post("/wfh/<int:wfh_id>/approve")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def wfh_approve(wfh_id):
    err = _hr_only()
    if err: return err

    obj = WFHRequest.query.filter_by(id=wfh_id, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    obj.status = "APPROVED"
    obj.action_by = _user_id()
    obj.action_at = datetime.utcnow()
    db.session.commit()
    return _json_ok({"id": obj.id, "Status": obj.status}, "Approved")


@hr_docs_bp.post("/wfh/<int:wfh_id>/reject")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def wfh_reject(wfh_id):
    err = _hr_only()
    if err: return err

    obj = WFHRequest.query.filter_by(id=wfh_id, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    payload = request.get_json(silent=True) or {}
    obj.status = "REJECTED"
    obj.comments = payload.get("comments")
    obj.action_by = _user_id()
    obj.action_at = datetime.utcnow()
    db.session.commit()
    return _json_ok({"id": obj.id, "Status": obj.status}, "Rejected")


# =========================================================
# TAB 5: GENERAL HR DOCUMENTS
# HR can upload, others view; download for ALL? (you didn't restrict, so keeping download allowed)
# If you want download HR-only, tell me, I will lock it too.
# =========================================================
@hr_docs_bp.get("/documents")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN", "EMPLOYEE"])
def documents_list_general():
    """Unified General Documents List"""
    q = HRDocument.query
    if g.user.role not in ['SUPER_ADMIN']:
        q = q.filter_by(company_id=_company_id())
    
    if g.user.role in ['EMPLOYEE', 'MANAGER']:
        q = q.filter_by(is_active=True, is_sensitive=False)

    items = q.order_by(HRDocument.created_at.desc()).all()
    data = [{
        "id": x.id,
        "title": x.title,
        "category": x.category,
        "status": x.status,
        "is_active": x.is_active,
        "is_sensitive": x.is_sensitive,
        "created_at": x.created_at.isoformat(),
        "views": x.view_count or 0
    } for x in items]
    return _json_ok(data)


@hr_docs_bp.post("/documents")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN", "EMPLOYEE"])
def documents_upload():
    err = _hr_only()
    if err: return err

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400

    file = request.files['file']
    title = request.form.get("title")
    category = request.form.get("category")

    if not title or not file or file.filename == '':
        return jsonify({"success": False, "message": "Title and valid File required"}), 400

    folder = os.path.join(current_app.root_path, "uploads", "general_docs")
    os.makedirs(folder, exist_ok=True)

    filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
    path = os.path.join(folder, filename)
    file.save(path)

    doc = HRDocument(
        company_id=_company_id(),
        title=title,
        category=category,
        file_path=path,
        created_by=_user_id()
    )
    db.session.add(doc)
    db.session.commit()
    return _json_ok({"id": doc.id}, "Document uploaded")


@hr_docs_bp.get("/documents/<int:did>/download")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN", "EMPLOYEE"])
def documents_download_general(did):
    doc = HRDocument.query.filter_by(id=did).first_or_404()
    if g.user.role not in ['SUPER_ADMIN'] and doc.company_id != _company_id():
        return jsonify({"success": False, "message": "Access denied"}), 403
    
    # Restrict sensitive
    if doc.is_sensitive and g.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return jsonify({"success": False, "message": "Document is restricted"}), 403

    if not doc or not os.path.exists(doc.file_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    # Activity log for higher authorities
    log_action("DOCUMENT_PREPARE", "HRDocument", doc.id, 200, meta={"title": doc.title, "user": g.user.email})
    doc.view_count = (doc.view_count or 0) + 1
    doc.last_viewed_at = datetime.utcnow()
    db.session.commit()

    return send_file(doc.file_path, as_attachment=True)

# ---------------------------------------------------------
# NEW: Toggle Document Status & Activity Monitoring
# ---------------------------------------------------------

@hr_docs_bp.post("/documents/<int:did>/toggle")
@token_required
@role_required(["ADMIN", "SUPER_ADMIN", "HR"])
def toggle_document_status(did):
    """Activate/Deactivate Documents with Audit Log"""
    doc = HRDocument.query.get_or_404(did)
    if g.user.role != "SUPER_ADMIN" and doc.company_id != _company_id():
        return jsonify({"success": False, "message": "Access denied"}), 403

    doc.is_active = not doc.is_active
    doc.status = "Active" if doc.is_active else "Inactive"
    
    action = "DOCUMENT_ACTIVATE" if doc.is_active else "DOCUMENT_DEACTIVATE"
    log_action(action, "HRDocument", doc.id, 200, meta={"title": doc.title})
    
    db.session.commit()
    return _json_ok({"status": doc.status, "is_active": doc.is_active}, f"Document {doc.status}")

@hr_docs_bp.get("/activity/logs")
@token_required
@role_required(["ADMIN", "SUPER_ADMIN", "HR"])
def get_document_activity():
    """Visibility for Higher Authorities to see Employee Actions"""
    q = AuditLog.query.filter(AuditLog.action.in_(['DOCUMENT_VIEW', 'DOCUMENT_PREPARE']))
    
    if g.user.role != "SUPER_ADMIN":
        q = q.filter_by(company_id=_company_id())
    
    items = q.order_by(AuditLog.created_at.desc()).limit(100).all()
    
    data = [{
        "id": x.id,
        "timestamp": x.created_at.isoformat(),
        "user_id": x.user_id,
        "role": x.role,
        "action": x.action,
        "document_name": x.meta if x.meta else "N/A",
        "ip": x.ip_address
    } for x in items]
    
    return _json_ok(data)
