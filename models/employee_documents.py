from models.master import db
from datetime import datetime

class EmployeeDocument(db.Model):
    __tablename__ = "employee_documents"

    document_id = db.Column(db.Integer, primary_key=True)
    onboard_id = db.Column(db.Integer, nullable=False)

    document_type = db.Column(db.String(100), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)

    uploaded_date = db.Column(db.DateTime, default=datetime.utcnow)
    verified_status = db.Column(db.String(50), default="Pending")

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "onboard_id": self.onboard_id,
            "document_type": self.document_type,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "uploaded_date": self.uploaded_date.isoformat() if self.uploaded_date else None,
            "verified_status": self.verified_status
        }
