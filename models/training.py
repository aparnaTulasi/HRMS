# models/training.py
from datetime import datetime
from models import db

class TrainingProgram(db.Model):
    __tablename__ = "training_programs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, nullable=False, index=True)
    
    title = db.Column(db.String(255), nullable=False)
    trainer_platform = db.Column(db.String(150), nullable=True) # UI: Trainer / Platform
    start_date = db.Column(db.Date, nullable=False)
    duration = db.Column(db.String(50), nullable=True)         # UI: 2 Weeks, 4 Hours
    training_hours = db.Column(db.Integer, default=0)         # For stats
    description = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(30), default="Upcoming")      # Upcoming, In Progress, Completed
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TrainingParticipant(db.Model):
    __tablename__ = "training_participants"

    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey("training_programs.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    
    completion_rate = db.Column(db.Integer, default=0)         # 0-100
    status = db.Column(db.String(30), default="Joined")        # Joined, Completed
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    training = db.relationship("TrainingProgram", backref=db.backref("participants", cascade="all, delete-orphan"))
    employee = db.relationship("Employee", foreign_keys=[employee_id])

class TrainingMaterial(db.Model):
    __tablename__ = "training_materials"

    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer, db.ForeignKey("training_programs.id"), nullable=False)
    
    title = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=True) # PDF, DOC, Video
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    training = db.relationship("TrainingProgram", backref=db.backref("materials", cascade="all, delete-orphan"))
