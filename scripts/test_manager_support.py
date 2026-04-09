import sys
import os
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.support_ticket import SupportTicket
from flask import g

def setup_test_data():
    with app.app_context():
        # Clear existing test data if any
        User.query.filter(User.email.like('test_%')).delete(synchronize_session=False)
        db.session.commit()

        # Create Manager
        manager_user = User(email='test_manager@example.com', role='MANAGER', status='ACTIVE')
        db.session.add(manager_user)
        db.session.flush()
        
        manager_emp = Employee(user_id=manager_user.id, company_id=1, full_name='Test Manager', employee_id='MGR001')
        db.session.add(manager_emp)
        db.session.flush()

        # Create Subordinate
        sub_user = User(email='test_sub@example.com', role='EMPLOYEE', status='ACTIVE')
        db.session.add(sub_user)
        db.session.flush()
        
        sub_emp = Employee(user_id=sub_user.id, company_id=1, full_name='Test Subordinate', employee_id='EMP001', manager_id=manager_emp.id)
        db.session.add(sub_emp)
        db.session.flush()

        # Create Other User (not in team)
        other_user = User(email='test_other@example.com', role='EMPLOYEE', status='ACTIVE')
        db.session.add(other_user)
        db.session.flush()
        
        other_emp = Employee(user_id=other_user.id, company_id=1, full_name='Other Guy', employee_id='EMP002')
        db.session.add(other_emp)
        db.session.flush()

        # Create Tickets
        t1 = SupportTicket(ticket_id='SUP-101', subject='Manager Ticket', category='IT Support', created_by=manager_user.id, company_id=1, description='Test')
        t2 = SupportTicket(ticket_id='SUP-102', subject='Subordinate Ticket', category='Payroll', created_by=sub_user.id, company_id=1, description='Test')
        t3 = SupportTicket(ticket_id='SUP-103', subject='Other Ticket', category='IT Support', created_by=other_user.id, company_id=1, description='Test')
        
        db.session.add_all([t1, t2, t3])
        db.session.commit()
        return manager_user.id, sub_user.id, other_user.id

def test_manager_visibility(manager_user_id):
    from routes.support import get_tickets
    with app.app_context():
        # Mock g.user
        g.user = User.query.get(manager_user_id)
        
        # Call the route logic (simulate)
        from routes.support import get_tickets
        # We need to simulate the request context if we call the route directly,
        # or just import the logic. Since get_tickets is a route, we can call it.
        with app.test_request_context():
            g.user = User.query.get(manager_user_id)
            response, code = get_tickets()
            data = response.get_json()
            
            print(f"Manager ({g.user.email}) saw {len(data['data'])} tickets.")
            for t in data['data']:
                print(f" - {t['id']}: {t['subject']}")
            
            # Expecting 2 tickets (Manager's own and Subordinate's)
            assert len(data['data']) == 2
            subjects = [t['subject'] for t in data['data']]
            assert 'Manager Ticket' in subjects
            assert 'Subordinate Ticket' in subjects
            assert 'Other Ticket' not in subjects
            print("Manager visibility test PASSED.")

if __name__ == '__main__':
    mgr_id, sub_id, other_id = setup_test_data()
    try:
        test_manager_visibility(mgr_id)
    finally:
        # Cleanup
        with app.app_context():
            # SupportTicket.query.filter(SupportTicket.ticket_id.in_(['SUP-101', 'SUP-102', 'SUP-103'])).delete()
            # Employee.query.filter(Employee.user_id.in_([mgr_id, sub_id, other_id])).delete()
            # User.query.filter(User.id.in_([mgr_id, sub_id, other_id])).delete()
            # db.session.commit()
            print("Cleanup skipped for manual verification if needed.")
