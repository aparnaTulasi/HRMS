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
from utils.decorators import token_required, role_required

# NOTE: Make sure these models exist in models/hr_documents.py
from models.hr_documents import (
    OnboardingCandidate,
    LetterTemplate,
    LetterRequest,
    CertificateIssue,
    WFHRequest,
    HRDocument
)

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


@hr_docs_bp.post("/letters/templates/seed")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def letters_seed_templates():
    err = _hr_only()
    if err: return err

    defaults = [
        ("OFFER", "Offer Letter", "<h2>Offer Letter</h2><p>Dear {{employee_name}},</p><p>We offer you {{designation}} with CTC {{ctc}}.</p>"),
        ("APPOINTMENT", "Appointment Letter", "<h2>Appointment Letter</h2><p>Welcome {{employee_name}} as {{designation}}.</p>"),
        ("INCREMENT", "Increment Letter", "<h2>Increment Letter</h2><p>Your new CTC is {{ctc}} effective {{effective_date}}.</p>"),
        ("RELIEVING", "Relieving Letter", "<h2>Relieving Letter</h2><p>{{employee_name}} relieved on {{last_working_day}}.</p>"),
        ("PERFORMANCE", "Performance Review", "<h2>Performance Review</h2><p>{{employee_name}} rating: {{rating}}.</p>"),
    ]

    created = 0
    for t, title, body in defaults:
        exists = LetterTemplate.query.filter_by(company_id=_company_id(), letter_type=t, is_active=True).first()
        if not exists:
            db.session.add(LetterTemplate(
                company_id=_company_id(),
                letter_type=t,
                title=title,
                body_html=body,
                is_active=True,
                version_no=1,
                created_by=_user_id()
            ))
            created += 1

    db.session.commit()
    return _json_ok({"created": created}, "Templates seeded")


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
        letter_date=date.fromisoformat(letter_date_str),
        template_option=template_option,
        send_email_copy=send_copy,
        status="GENERATED",
        payload=context,
        current_version=1,
        created_by=_user_id()
    )
    db.session.add(req)
    db.session.flush()

    # Generate file
    rendered = _render_template(tmpl.body_html, context)
    file_path = _save_text_as_file(rendered, f"letter_{letter_type.lower()}_{req.id}_v1")
    req.pdf_path = file_path

    # Send email if checked
    email_status = "Not Sent"
    if send_copy:
        subject = f"{tmpl.title} - {employee_name}"
        body = f"Hello {employee_name},\n\nPlease find attached your {tmpl.title}.\nDate: {letter_date_str}\n\nRegards,\nHR Team"
        sent = _send_email_with_attachment(employee_email, subject, body, file_path)
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
    recipient_email = payload.get("RecipientEmail")
    issue_date_str = payload.get("Date")
    template_option = payload.get("TemplateOption", "Standard Format")
    send_copy = bool(payload.get("SendEmailCopyToEmployee", False))
    details = payload.get("Details") or {}

    if not cert_type or not recipient or not recipient_email or not issue_date_str:
        return jsonify({"success": False, "message": "CertificateType, Recipient, RecipientEmail, Date required"}), 400

    # Dynamic content
    context = {
        "recipient": recipient,
        "recipient_email": recipient_email,
        "date": issue_date_str,
        "template_option": template_option,
        **details
    }

    content = (
        f"{cert_type}\n"
        f"Recipient: {recipient}\n"
        f"Date: {issue_date_str}\n"
        f"Template: {template_option}\n\n"
    )
    if details:
        content += "Details:\n"
        for k, v in details.items():
            content += f"- {k}: {v}\n"

    file_path = _save_text_as_file(content, f"certificate_{cert_type.lower()}")

    obj = CertificateIssue(
        company_id=_company_id(),
        recipient=recipient,
        certificate_type=cert_type,
        issue_date=date.fromisoformat(issue_date_str),
        recipient_email=recipient_email,
        template_option=template_option,
        send_email_copy=send_copy,
        payload=context,
        pdf_path=file_path,
        issued_by=_user_id()
    )
    db.session.add(obj)
    db.session.commit()

    email_status = "Not Sent"
    if send_copy:
        subject = f"{cert_type.replace('_',' ')} - {recipient}"
        body = f"Hello {recipient},\n\nPlease find attached your {cert_type.replace('_',' ')}.\nDate: {issue_date_str}\n\nRegards,\nHR Team"
        sent = _send_email_with_attachment(recipient_email, subject, body, file_path)
        email_status = "Sent" if sent else "Failed"

    abs_download = request.host_url.rstrip("/") + f"/api/hr-docs/certificates/{obj.id}/download"

    return _json_ok({
        "CertificateId": obj.id,
        "Recipient": recipient,
        "CertificateType": cert_type,
        "IssueDate": issue_date_str,
        "EmailStatus": email_status,
        "DownloadUrl": f"/api/hr-docs/certificates/{obj.id}/download",
        "DownloadUrlAbsolute": abs_download
    }, "Certificate issued")


@hr_docs_bp.get("/certificates/history")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_history():
    items = CertificateIssue.query.filter_by(company_id=_company_id()) \
        .order_by(CertificateIssue.created_at.desc()).all()

    data = [{
        "CertificateId": x.id,
        "Recipient": x.recipient,
        "CertificateType": x.certificate_type,
        "IssueDate": (x.payload or {}).get("date"),
        "ReadOnly": _is_read_only(),
        "CanDownload": (g.user.role == "HR")
    } for x in items]
    return _json_ok(data)


@hr_docs_bp.get("/certificates/<int:cid>/view")
@token_required
@role_required(["HR", "ADMIN", "SUPER_ADMIN"])
def certificates_view(cid):
    obj = CertificateIssue.query.filter_by(id=cid, company_id=_company_id()).first()
    if not obj:
        return jsonify({"success": False, "message": "Not found"}), 404

    return _json_ok({
        "CertificateId": obj.id,
        "Recipient": obj.recipient,
        "RecipientEmail": getattr(obj, "recipient_email", None),
        "CertificateType": obj.certificate_type,
        "IssueDate": obj.issue_date.isoformat() if obj.issue_date else None,
        "TemplateOption": getattr(obj, "template_option", None),
        "Payload": obj.payload,
        "ReadOnly": _is_read_only(),
        "CanDownload": (g.user.role == "HR")
    })


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
def documents_list():
    items = HRDocument.query.filter_by(company_id=_company_id()).order_by(HRDocument.created_at.desc()).all()
    data = [{
        "id": x.id,
        "title": x.title,
        "category": x.category,
        "created_at": x.created_at.isoformat()
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
def documents_download(did):
    doc = HRDocument.query.filter_by(id=did, company_id=_company_id()).first()
    if not doc or not os.path.exists(doc.file_path):
        return jsonify({"success": False, "message": "File not found"}), 404
    return send_file(doc.file_path, as_attachment=True)
