from models import db

class SquadMember(db.Model):
    __tablename__ = 'squad_members'
    
    id = db.Column(db.Integer, primary_key=True)
    squad_id = db.Column(db.Integer, db.ForeignKey('squads.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    role = db.Column(db.String(50)) # Lead, Developer, etc.
    
    employee = db.relationship('Employee', backref='squad_memberships', lazy=True)
