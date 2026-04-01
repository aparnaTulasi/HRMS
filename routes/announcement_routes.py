from flask import Blueprint, request, jsonify, g
from models import db
from models.announcement import Announcement
from utils.decorators import token_required, role_required
from datetime import datetime, date

announcement_bp = Blueprint('announcement', __name__)

@announcement_bp.route('/list', methods=['GET'])
@token_required
def get_announcements():
    today = datetime.utcnow()
    # Fetch active announcements for the company or global (None)
    q = Announcement.query.filter(
        Announcement.is_active == True,
        (Announcement.expiry_date == None) | (Announcement.expiry_date >= today)
    )
    
    if g.user.role != 'SUPER_ADMIN':
        q = q.filter((Announcement.company_id == g.user.company_id) | (Announcement.company_id == None))
    
    announcements = q.order_by(Announcement.priority.desc(), Announcement.created_at.desc()).all()
    
    return jsonify({
        "success": True,
        "announcements": [a.to_dict() for a in announcements]
    })

@announcement_bp.route('/create', methods=['POST'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN'])
def create_announcement():
    data = request.get_json()
    
    if not data.get('title') or not data.get('message'):
        return jsonify({"message": "Title and Message are required"}), 400
        
    expiry = None
    if data.get('expiry_date'):
        try:
            expiry = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
        except ValueError:
            return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400

    new_announcement = Announcement(
        company_id=g.user.company_id if g.user.role != 'SUPER_ADMIN' else data.get('company_id'),
        title=data['title'],
        message=data['message'],
        priority=data.get('priority', 'NORMAL'),
        category=data.get('category', 'General'),
        expiry_date=expiry,
        created_by=g.user.id
    )
    
    db.session.add(new_announcement)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Announcement posted successfully",
        "announcement_id": new_announcement.id
    }), 201

@announcement_bp.route('/<int:announcement_id>', methods=['PUT', 'PATCH'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN'])
def update_announcement(announcement_id):
    a = Announcement.query.get(announcement_id)
    if not a:
        return jsonify({"message": "Announcement not found"}), 404
        
    if g.user.role != 'SUPER_ADMIN' and a.company_id != g.user.company_id:
        return jsonify({"message": "Permission denied"}), 403
        
    data = request.get_json()
    if 'title' in data: a.title = data['title']
    if 'message' in data: a.message = data['message']
    if 'priority' in data: a.priority = data['priority']
    if 'category' in data: a.category = data['category']
    if 'is_active' in data: a.is_active = data['is_active']
    
    if 'expiry_date' in data:
        if data['expiry_date']:
            try:
                a.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d')
            except ValueError:
                return jsonify({"message": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            a.expiry_date = None

    db.session.commit()
    return jsonify({"success": True, "message": "Announcement updated successfully"})

@announcement_bp.route('/<int:announcement_id>', methods=['DELETE'])
@token_required
@role_required(['ADMIN', 'HR', 'SUPER_ADMIN'])
def delete_announcement(announcement_id):
    a = Announcement.query.get(announcement_id)
    if not a:
        return jsonify({"message": "Announcement not found"}), 404
        
    if g.user.role != 'SUPER_ADMIN' and a.company_id != g.user.company_id:
        return jsonify({"message": "Permission denied"}), 403
        
    db.session.delete(a)
    db.session.commit()
    return jsonify({"success": True, "message": "Announcement removed"}), 200
