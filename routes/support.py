from flask import Blueprint, request, jsonify, g
from models import db
from models.support_ticket import SupportTicket
from utils.decorators import token_required
from datetime import datetime

support_bp = Blueprint('support', __name__)

@support_bp.route('/config', methods=['GET'])
@token_required
def get_support_config():
    """
    Returns the available options for Category and Priority drop-downs.
    """
    return jsonify({
        "success": True,
        "data": {
            "categories": ["IT Support", "Payroll", "HR Query", "Office Admin", "Others"],
            "priorities": ["Low", "Medium", "High", "Urgent"]
        }
    }), 200

@support_bp.route('/tickets', methods=['GET'])
@token_required
def get_tickets():
    try:
        # Hierarchical View
        if g.user.role == 'SUPER_ADMIN':
            tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
        elif g.user.role in ['ADMIN', 'HR']:
            tickets = SupportTicket.query.filter_by(company_id=g.user.company_id).order_by(SupportTicket.created_at.desc()).all()
        else:
            # Employee sees only their own
            tickets = SupportTicket.query.filter_by(created_by=g.user.id, company_id=g.user.company_id).order_by(SupportTicket.created_at.desc()).all()
            
        return jsonify({
            "success": True,
            "data": [t.to_dict() for t in tickets]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to fetch tickets', 'error': str(e)}), 500

@support_bp.route('/dashboard-stats', methods=['GET'])
@token_required
def get_dashboard_stats():
    try:
        q = SupportTicket.query.filter_by(company_id=g.user.company_id)
        
        # If standard employee, show their own stats
        if g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
            q = q.filter_by(created_by=g.user.id)
            
        tickets = q.all()
        
        total = len(tickets)
        open_count = len([t for t in tickets if t.status == 'Open'])
        in_progress = len([t for t in tickets if t.status == 'In Progress'])
        resolved = len([t for t in tickets if t.status in ['Resolved', 'Closed']])
        
        return jsonify({
            'success': True,
            'data': {
                'total_tickets': total,
                'open': open_count,
                'in_progress': in_progress,
                'resolved': resolved
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'Failed to fetch dashboard stats', 'error': str(e)}), 500

@support_bp.route('/tickets', methods=['POST'])
@token_required
def create_ticket():
    data = request.get_json()
    try:
        # Generate Sequential ID: SUP-001 per company
        last_ticket = SupportTicket.query.filter_by(company_id=g.user.company_id).order_by(SupportTicket.id.desc()).first()
        if last_ticket and last_ticket.ticket_id.startswith('SUP-'):
            try:
                last_num = int(last_ticket.ticket_id.split('-')[1])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        new_ticket_id = f"SUP-{new_num:03d}"
        
        new_ticket = SupportTicket(
            ticket_id=new_ticket_id,
            subject=data.get('subject'),
            category=data.get('category'),
            priority=data.get('priority', 'Low'),
            status='Open',
            description=data.get('description'),
            attachment_url=data.get('attachment_url'),
            company_id=g.user.company_id,
            created_by=g.user.id
        )
        db.session.add(new_ticket)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Ticket created successfully',
            'data': new_ticket.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to create ticket', 'error': str(e)}), 500

@support_bp.route('/tickets/<int:id>/action', methods=['PATCH'])
@token_required
def ticket_action(id):
    """
    Standardize the action endpoint for Approve/Reject/Status Update
    """
    data = request.get_json()
    try:
        ticket = SupportTicket.query.filter_by(id=id, company_id=g.user.company_id).first()
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404
            
        # Role check for management actions
        if g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN']:
            return jsonify({'success': False, 'message': 'Unauthorized to change ticket status'}), 403

        if 'status' in data:
            ticket.status = data['status'] # e.g. "In Progress", "Resolved"
        if 'priority' in data:
            ticket.priority = data['priority']
            
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f"Ticket updated to {ticket.status}",
            'data': ticket.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update ticket', 'error': str(e)}), 500
