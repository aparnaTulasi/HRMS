from models import db

# NOTE: The following models are for the "Advanced" option (separate tables).
# The current implementation uses JSON fields in the `employees` table for simplicity.
# These can be re-enabled later if a more structured approach is needed.
#
# class EmployeeEducation(db.Model):
#     __tablename__ = 'employee_education'
#     id = db.Column(db.Integer, primary_key=True)
#     employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
#     degree = db.Column(db.String(100))
#     institution = db.Column(db.String(200))
#     passing_year = db.Column(db.Integer)
#     grade = db.Column(db.String(20))
#
# class EmployeeExperience(db.Model):
#     __tablename__ = 'employee_experience'
#     id = db.Column(db.Integer, primary_key=True)
#     employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
#     company_name = db.Column(db.String(100))
#     designation = db.Column(db.String(100))
#     from_date = db.Column(db.Date)
#     to_date = db.Column(db.Date)
#     description = db.Column(db.Text)