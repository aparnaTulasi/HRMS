from flask import Blueprint, request, jsonify, g
from models import db
from models.feedback import Feedback
from utils.decorators import token_required

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/feedback', methods=['POST'])
@token_required
def submit_feedback():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400
        
    rating = data.get('rating') # E.g., 'Loved It!'
    category = data.get('category') # E.g., 'User Interface'
    comments = data.get('comments')
    
    if not rating or not category:
        return jsonify({'message': 'Rating and Category are required'}), 400
        
    try:
        new_feedback = Feedback(
            user_id=g.user.id,
            rating=rating,
            category=category,
            comments=comments,
            company_id=g.user.company_id
        )
        db.session.add(new_feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!',
            'data': new_feedback.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to save feedback', 'error': str(e)}), 500

@feedback_bp.route('/feedback/list', methods=['GET'])
@token_required
def get_feedback_list():
    # Only Admin, Super Admin, HR can see feedback
    if g.user.role not in ['SUPER_ADMIN', 'ADMIN', 'HR']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    try:
        if g.user.role == 'SUPER_ADMIN':
            feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
        else:
            feedbacks = Feedback.query.filter_by(company_id=g.user.company_id).order_by(Feedback.created_at.desc()).all()
            
        return jsonify({
            'success': True,
            'data': [f.to_dict() for f in feedbacks]
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch feedback', 'error': str(e)}), 500
