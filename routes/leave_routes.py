from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models.leave import Leave, LeaveType
from models.employee import Employee
from models import db
from datetime import datetime

leave_bp = Blueprint('leave', __name__, url_prefix='/leave')

@leave_bp.route('/')
@login_required
def leave_dashboard():
    """Leave dashboard for employee"""
    # Get employee's leave history
    leaves = Leave.query.filter_by(employee_id=current_user.id).order_by(
        Leave.created_at.desc()
    ).all()
    
    # Get available leave types
    leave_types = LeaveType.query.filter_by(is_active=True).all()
    
    return render_template('leave/dashboard.html', 
                          leaves=leaves, 
                          leave_types=leave_types)

@leave_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply_leave():
    """Apply for leave"""
    if request.method == 'POST':
        try:
            leave_type = request.form.get('leave_type')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            reason = request.form.get('reason')
            
            # Create new leave application
            new_leave = Leave(
                employee_id=current_user.id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                status='pending'
            )
            
            db.session.add(new_leave)
            db.session.commit()
            
            flash('Leave application submitted successfully!', 'success')
            return redirect(url_for('leave.leave_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error applying leave: {str(e)}', 'error')
    
    # GET request - show form
    leave_types = LeaveType.query.filter_by(is_active=True).all()
    return render_template('leave/apply.html', leave_types=leave_types)

@leave_bp.route('/manage')
@login_required
def manage_leaves():
    """For managers/HR to manage leave applications"""
    # Check if user has permission to manage leaves
    # You'll need to implement permission check
    
    pending_leaves = Leave.query.filter_by(status='pending').all()
    return render_template('leave/manage.html', leaves=pending_leaves)

@leave_bp.route('/approve/<int:leave_id>')
@login_required
def approve_leave(leave_id):
    """Approve a leave request"""
    leave = Leave.query.get_or_404(leave_id)
    leave.status = 'approved'
    leave.approved_by = current_user.id
    leave.approved_date = datetime.utcnow()
    
    db.session.commit()
    flash('Leave approved successfully!', 'success')
    return redirect(url_for('leave.manage_leaves'))

@leave_bp.route('/reject/<int:leave_id>')
@login_required
def reject_leave(leave_id):
    """Reject a leave request"""
    leave = Leave.query.get_or_404(leave_id)
    leave.status = 'rejected'
    leave.approved_by = current_user.id
    leave.approved_date = datetime.utcnow()
    
    db.session.commit()
    flash('Leave rejected!', 'warning')
    return redirect(url_for('leave.manage_leaves'))

@leave_bp.route('/api/leave-types')
@login_required
def get_leave_types():
    """API endpoint to get leave types (for dropdowns)"""
    types = LeaveType.query.filter_by(is_active=True).all()
    return jsonify([{'id': t.id, 'name': t.name, 'max_days': t.max_days_per_year} for t in types])

@leave_bp.route('/api/balance/<int:employee_id>')
@login_required
def get_leave_balance(employee_id):
    """API endpoint to get employee's leave balance"""
    # This is a simplified version - you might want to create a LeaveBalance model
    leaves_taken = Leave.query.filter_by(
        employee_id=employee_id,
        status='approved'
    ).count()
    
    # Assuming 12 days annual leave per year
    total_available = 12
    balance = total_available - leaves_taken
    
    return jsonify({
        'total_available': total_available,
        'leaves_taken': leaves_taken,
        'balance': balance
    })