# models/hr_documents.py
from datetime import datetime, date
from models import db
from models.employee import Employee

class OnboardingCandidate(db.Model):
    __tablename__ = "onboarding_candidates"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    candidate = db.Column(db.String(150), nullable=False)   # UI: Candidate
    role = db.Column(db.String(120), nullable=True)         # UI: Role
    joining_date = db.Column(db.Date, nullable=True)        # UI: Joining Date

    status = db.Column(db.String(30), default="IN_PROGRESS")   # UI: Status
    progress = db.Column(db.Integer, default=0)                # UI: Progress (0-100)

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LetterTemplate(db.Model):
    __tablename__ = "letter_templates"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    letter_type = db.Column(db.String(40), nullable=False, index=True)  # OFFER/APPOINTMENT/INCREMENT/RELIEVING/PERFORMANCE
    title = db.Column(db.String(120), nullable=False)                  # UI card title
    category = db.Column(db.String(50), nullable=True)                 # Recruitment, Onboarding, Performance, Exit, General
    
    resource_url = db.Column(db.String(255), nullable=True)
    blog_link = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="Active")                # Active, Draft
    usage_count = db.Column(db.Integer, default=0)

    body_html = db.Column(db.Text, nullable=False)                     # template with {{var}}

    is_active = db.Column(db.Boolean, default=True)
    version_no = db.Column(db.Integer, default=1)

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LetterTemplateVersion(db.Model):
    __tablename__ = "letter_template_versions"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("letter_templates.id"), nullable=False, index=True)
    version_no = db.Column(db.Integer, nullable=False)
    body_snapshot = db.Column(db.Text, nullable=False)
    changed_by = db.Column(db.Integer, nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(255), nullable=True)


class LetterRequest(db.Model):
    __tablename__ = "letter_requests"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    employee_id = db.Column(db.Integer, nullable=True, index=True)   # if employee
    candidate_id = db.Column(db.Integer, nullable=True, index=True)  # if onboarding candidate

    employee_name = db.Column(db.String(150), nullable=True)
    employee_email = db.Column(db.String(150), nullable=True)
    letter_date = db.Column(db.Date, nullable=True)
    template_option = db.Column(db.String(50), default="Standard Format")
    send_email_copy = db.Column(db.Boolean, default=False)

    letter_type = db.Column(db.String(40), nullable=False, index=True)
    template_id = db.Column(db.Integer, db.ForeignKey("letter_templates.id"), nullable=True)

    status = db.Column(db.String(30), default="DRAFT")  # DRAFT/IN_REVIEW/APPROVED/REJECTED/ISSUED/SIGNED
    payload = db.Column(db.JSON, nullable=True)         # dynamic variables snapshot
    pdf_path = db.Column(db.String(255), nullable=True)

    current_version = db.Column(db.Integer, default=1)

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LetterRequestVersion(db.Model):
    __tablename__ = "letter_request_versions"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("letter_requests.id"), nullable=False, index=True)
    version_no = db.Column(db.Integer, nullable=False)

    payload_snapshot = db.Column(db.JSON, nullable=True)
    pdf_path = db.Column(db.String(255), nullable=True)

    issued_by = db.Column(db.Integer, nullable=True)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.String(255), nullable=True)


class LetterApprovalStep(db.Model):
    __tablename__ = "letter_approval_steps"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("letter_requests.id"), nullable=False, index=True)

    step_no = db.Column(db.Integer, nullable=False)
    approver_role = db.Column(db.String(40), nullable=False)          # HR_MANAGER / ADMIN / DIRECTOR etc

    status = db.Column(db.String(20), default="PENDING")             # PENDING/APPROVED/REJECTED
    action_by = db.Column(db.Integer, nullable=True)
    action_at = db.Column(db.DateTime, nullable=True)
    comments = db.Column(db.String(255), nullable=True)


class EsignProvider(db.Model):
    __tablename__ = "esign_providers"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    provider = db.Column(db.String(40), nullable=False)              # DOCUSIGN/ADOBE/ZOHO
    api_key_encrypted = db.Column(db.Text, nullable=True)
    account_id = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EsignEnvelope(db.Model):
    __tablename__ = "esign_envelopes"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("letter_requests.id"), nullable=False, index=True)
    provider = db.Column(db.String(40), nullable=False)
    envelope_id = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), default="SENT")  # SENT/SIGNED/DECLINED/EXPIRED
    signed_pdf_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CertificateIssue(db.Model):
    __tablename__ = "certificate_issues"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    recipient = db.Column(db.String(150), nullable=False)     # UI: Recipient
    certificate_type = db.Column(db.String(100), nullable=False) # UI: Certificate Type
    issue_date = db.Column(db.Date, nullable=False, default=date.today) # UI: Issue Date

    recipient_email = db.Column(db.String(150), nullable=True)
    template_option = db.Column(db.String(50), default="Standard Format")
    send_email_copy = db.Column(db.Boolean, default=False)

    employee_id = db.Column(db.Integer, nullable=True, index=True)
    payload = db.Column(db.JSON, nullable=True)
    pdf_path = db.Column(db.String(255), nullable=True)

    issued_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WFHRequest(db.Model):
    __tablename__ = "wfh_requests"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    employee_name = db.Column(db.String(150), nullable=True, name="employee") # Map to existing DB column "employee"
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True, index=True)

    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="PENDING")  # PENDING, APPROVED, REJECTED
    comments = db.Column(db.Text, nullable=True) # For rejection comments

    created_by = db.Column(db.Integer, nullable=True)
    action_by = db.Column(db.Integer, nullable=True) # approver/rejector
    action_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee_rel = db.relationship("Employee", foreign_keys=[employee_id])


class HRDocument(db.Model):
    __tablename__ = "hr_documents"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=True) # Policy, Handbook, Form
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.String(20), nullable=True)
    file_type = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default="Active") # Active, Inactive
    is_sensitive = db.Column(db.Boolean, default=False) # Restricted to Admin/Super Admin
    
    last_viewed_at = db.Column(db.DateTime, nullable=True) # Last viewed by any user
    view_count = db.Column(db.Integer, default=0) # Total number of times viewed/downloaded

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LetterApprovalWorkflow(db.Model):
    __tablename__ = "letter_approval_workflows"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    
    name = db.Column(db.String(150), nullable=False)
    letter_type = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(20), default="Active")  # Active, Draft
    is_active = db.Column(db.Boolean, default=True)      # Soft delete

    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LetterApprovalWorkflowLevel(db.Model):
    __tablename__ = "letter_approval_workflow_levels"

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey("letter_approval_workflows.id"), nullable=False)
    
    step_no = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(50), nullable=False)    # HR Manager, Dept Head, CEO, etc.
    user_id = db.Column(db.Integer, nullable=True)      # Specific user if any

    workflow = db.relationship("LetterApprovalWorkflow", backref=db.backref("levels", cascade="all, delete-orphan"))

class LetterVariable(db.Model):
    __tablename__ = "letter_variables"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    
    name = db.Column(db.String(50), nullable=False)        # variable name like {{designation}}
    description = db.Column(db.String(255), nullable=True) # e.g. "Employee's Job Title"
    source = db.Column(db.String(20), default="System")    # System, Custom
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EsignRequest(db.Model):
    __tablename__ = "esign_requests"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    letter_type = db.Column(db.String(50), nullable=False)
    sent_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="Pending") # Pending, Signed, Overdue, Declined
    
    request_id = db.Column(db.Integer, db.ForeignKey("letter_requests.id"), nullable=True)
    
    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship("Employee", foreign_keys=[employee_id])

class EsignSettings(db.Model):
    __tablename__ = "esign_settings"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True, unique=True)
    
    otp_enabled = db.Column(db.Boolean, default=True)
    selfie_enabled = db.Column(db.Boolean, default=False)
    aadhaar_enabled = db.Column(db.Boolean, default=False)
    reminders_enabled = db.Column(db.Boolean, default=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
