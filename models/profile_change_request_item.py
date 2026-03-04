from models import db

class ProfileChangeRequestItem(db.Model):
    __tablename__ = 'profile_change_request_items'
    id = db.Column(db.Integer, primary_key=True)

    request_id = db.Column(db.Integer, db.ForeignKey('profile_change_requests.id'), nullable=False)

    # ✅ UI key must be same (no mismatch)
    field_key = db.Column(db.String(100), nullable=False)

    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)