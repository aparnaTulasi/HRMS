from flask import Blueprint, jsonify, g, request
from models import db
from models.notification import Notification
from utils.decorators import token_required
from datetime import datetime
from sqlalchemy import or_

notification_bp = Blueprint('notifications', __name__)

@notification_bp.route('/', methods=['GET'])
@token_required
def get_user_notifications():
    """
    Fetches latest notifications for the current user.
    Includes notifications targeted to their user_id OR their specific role.
    """
    user_id = g.user.id
    role = g.user.role
    
    # Fetch unread notifications for this user or their role
    notifications = Notification.query.filter(
        or_(
            Notification.user_id == user_id,
            Notification.role == role
        )
    ).filter_by(is_read=False).order_by(Notification.created_at.desc()).all()
    
    return jsonify({
        "success": True,
        "data": [n.to_dict() for n in notifications]
    }), 200

@notification_bp.route('/mark-read', methods=['PUT'])
@token_required
def mark_all_as_read():
    """
    Marks all notifications for the current user/role as read.
    """
    user_id = g.user.id
    role = g.user.role
    
    Notification.query.filter(
        or_(
            Notification.user_id == user_id,
            Notification.role == role
        )
    ).filter_by(is_read=False).update({Notification.is_read: True}, synchronize_session=False)
    
    db.session.commit()
    return jsonify({"success": True, "message": "All notifications marked as read"}), 200

@notification_bp.route('/<int:notif_id>/read', methods=['PUT'])
@token_required
def mark_one_as_read(notif_id):
    """
    Marks a specific notification as read.
    """
    notif = Notification.query.get_or_404(notif_id)
    
    # Ownership/Role check
    if notif.user_id != g.user.id and notif.role != g.user.role:
        return jsonify({"success": False, "message": "Access denied"}), 403
        
    notif.is_read = True
    db.session.commit()
    
    return jsonify({"success": True, "message": "Notification marked as read"}), 200
