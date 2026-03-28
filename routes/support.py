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
    Returns stats for the Support Dashboard cards:
    - Total Tickets
    - Open
    - In Progress
    - Resolved
    """
    try:
        q = SupportTicket.query
        if g.user.role != 'SUPER_ADMIN':
            q = q.filter_by(company_id=g.user.company_id)
        
        # If Employee, only show their own stats? 
        # Usually dashboard stats for "Support Helpdesk" are for the whole company if viewable by HR/Admin.
        # But if the user is an employee, they might only see their own.
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
        return jsonify({'message': 'Failed to fetch dashboard stats', 'error': str(e)}), 500

@support_bp.route('/tickets', methods=['POST'])
@token_required
def create_ticket():
    data = request.get_json()
    try:
        # Generate Sequential ID: SUP-001
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
        ticket = SupportTicket.query.get(id)
        if not ticket:
            return jsonify({'message': 'Ticket not found'}), 404
            
        # Permission check
        if g.user.role not in ['ADMIN', 'HR', 'SUPER_ADMIN'] and ticket.created_by != g.user.id:
            return jsonify({'message': 'Unauthorized'}), 403

        if 'status' in data:
            ticket.status = data['status']
        if 'priority' in data:
            ticket.priority = data['priority']
        if 'category' in data:
            ticket.category = data['category']
            
        db.session.commit()
        return jsonify({'message': 'Ticket updated successfully', 'ticket': ticket.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to update ticket', 'error': str(e)}), 500
