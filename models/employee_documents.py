from models.master import db
from datetime import datetime

class EmployeeDocument(db.Model):
    __tablename__ = "employee_documents"

    document_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False)

    document_type = db.Column(db.String(100), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)

    uploaded_by = db.Column(db.String(50))  # employee / hr / admin
    uploaded_date = db.Column(db.DateTime, default=datetime.utcnow)

    verified_status = db.Column(db.String(50), default="Pending")  
    verified_by = db.Column(db.String(50), nullable=True)
    verified_date = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "employee_id": self.employee_id,
            "document_type": self.document_type,
            "file_name": self.file_name,
            "uploaded_by": self.uploaded_by,
            "uploaded_date": self.uploaded_date.strftime("%d-%m-%Y") if self.uploaded_date else None,
            "verified_status": self.verified_status,
            "verified_by": self.verified_by,
            "verified_date": self.verified_date.strftime("%d-%m-%Y") if self.verified_date else None
        }