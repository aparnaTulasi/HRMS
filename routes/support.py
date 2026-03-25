from flask import Blueprint, request, jsonify, g
from models import db
from models.support_ticket import SupportTicket
from utils.decorators import token_required

support_bp = Blueprint('support', __name__)

@support_bp.route('/tickets', methods=['GET'])
@token_required
def get_tickets():
    try:
        if g.user.role == 'SUPER_ADMIN':
            tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
        elif g.user.role in ['ADMIN', 'HR']:
            tickets = SupportTicket.query.filter_by(company_id=g.user.company_id).order_by(SupportTicket.created_at.desc()).all()
        else:
            tickets = SupportTicket.query.filter_by(created_by=g.user.id).order_by(SupportTicket.created_at.desc()).all()
            
        return jsonify([t.to_dict() for t in tickets]), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Failed to fetch tickets', 'error': str(e)}), 500

@support_bp.route('/dashboard-stats', methods=['GET'])
@token_required
def get_dashboard_stats():
    """
    Returns stats for the Concierge & Support header cards:
    - Total Active
    - Pending Action
    - Resolution Rate
    """
    try:
        # Filter by company if not Super Admin
        q = SupportTicket.query
        if g.user.role != 'SUPER_ADMIN':
            q = q.filter_by(company_id=g.user.company_id)
            
        tickets = q.all()
        
        total_active = len([t for t in tickets if t.status in ['Open', 'In Progress']])
        pending_action = len([t for t in tickets if t.status == 'Open'])
        
        resolved = len([t for t in tickets if t.status == 'Closed'])
        total = len(tickets)
        resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_active': total_active,
                'pending_action': pending_action,
                'resolution_rate': f"{resolution_rate}%"
            }
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch dashboard stats', 'error': str(e)}), 500

@support_bp.route('/tickets', methods=['POST'])
@token_required
def create_ticket():
    data = request.get_json()
    try:
        import random
        new_ticket_id = f"#TKT-{random.randint(100, 999)}"
        new_ticket = SupportTicket(
            ticket_id=new_ticket_id,
            subject=data.get('subject'),
            category=data.get('category'),
            priority=data.get('priority', 'Medium'),
            status='Open',
            description=data.get('description'),
            company_id=g.user.company_id,
            created_by=g.user.id
        )
        db.session.add(new_ticket)
        db.session.commit()
        return jsonify({'message': 'Ticket created successfully', 'ticket': new_ticket.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'message': 'Failed to create ticket', 'error': str(e)}), 500

@support_bp.route('/tickets/<int:id>', methods=['PUT', 'PATCH'])
@token_required
def update_ticket(id):
    data = request.get_json()
    try:
        ticket = SupportTicket.query.filter_by(id=id).first()
        if not ticket:
            ticket = SupportTicket.query.filter_by(ticket_id=id).first() # fallback if passed #TKT
        if not ticket:
            return jsonify({'message': 'Ticket not found'}), 404
            
        if 'status' in data:
            ticket.status = data['status']
        if 'priority' in data:
            ticket.priority = data['priority']
            
        db.session.commit()
        return jsonify({'message': 'Ticket updated successfully', 'ticket': ticket.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update ticket', 'error': str(e)}), 500
