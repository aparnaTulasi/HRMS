import sys
import os
from datetime import datetime, date, timedelta

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.task import Task
from leave.models import LeaveRequest, Holiday
from flask import g

def setup_test_data():
    with app.app_context():
        # Clear existing test data
        User.query.filter(User.email.like('dash_test_%')).delete(synchronize_session=False)
        db.session.commit()

        # 1. Create Manager
        manager_user = User(email='dash_test_mgr@example.com', role='MANAGER', status='ACTIVE', company_id=1)
        db.session.add(manager_user)
        db.session.flush()
        
        manager_emp = Employee(user_id=manager_user.id, company_id=1, full_name='Ganesh Manager', employee_id='DASH_M01')
        db.session.add(manager_emp)

        # 2. Create Team Members (12 as per UI)
        team_emp_ids = []
        for i in range(12):
            u = User(email=f'dash_test_team_{i}@example.com', role='EMPLOYEE', status='ACTIVE', company_id=1)
            db.session.add(u)
            db.session.flush()
            e = Employee(user_id=u.id, company_id=1, full_name=f'Team Member {i}', manager_id=manager_user.id, employee_id=f'DASH_T{i:02d}')
            db.session.add(e)
            db.session.flush()
            team_emp_ids.append(e.id)

        # 3. Present Today (9 as per UI)
        today = date.today()
        for i in range(9):
            att = Attendance(employee_id=team_emp_ids[i], attendance_date=today, status='Present', total_minutes=480, company_id=1)
            db.session.add(att)

        # 4. Pending Tasks (5 as per UI)
        for i in range(5):
            t = Task(title=f'Test Task {i}', assigned_to_employee_id=team_emp_ids[i], status='Pending', company_id=1)
            db.session.add(t)

        # 5. Pending Leaves
        for i in range(2):
            l = LeaveRequest(employee_id=team_emp_ids[i], leave_type='Sick Leave', total_days=2, start_date=today, end_date=today + timedelta(days=1), status='Pending', company_id=1)
            db.session.add(l)

        # 6. Holidays
        if not Holiday.query.filter_by(name='Test Holiday').first():
            h = Holiday(name='Test Holiday', date=today + timedelta(days=5), company_id=1)
            db.session.add(h)

        db.session.commit()
        return manager_user.id

def test_manager_rich_dashboard(manager_user_id):
    with app.app_context():
        g.user = User.query.get(manager_user_id)
        
        from routes.dashboard_routes import _get_role_dashboard_stats
        
        with app.test_request_context():
            g.user = User.query.get(manager_user_id)
            resp = _get_role_dashboard_stats()
            data = resp.get_json()
            
            print(f"Status structure check: {data['success']}")
            assert data['success'] is True
            assert data['role'] == 'MANAGER'
            
            # Check Top Stats
            stats = data['data']['top_stats']
            print(f"Top Stats: {stats}")
            assert stats['total_team'] == 12
            assert stats['present_today'] == 9
            assert stats['pending_tasks'] == 5
            assert stats['avg_efficiency'] == '85%'
            assert stats['active_goals'] == 3
            
            # Check Trends (Line Chart)
            trends = data['data']['attendance_trends']
            print(f"Attendance Trends count: {len(trends)}")
            assert len(trends) == 7
            assert trends[-1]['present'] == 9 # Today has 9

            # Check Status (Donut Chart)
            donut = data['data']['todays_status']
            print(f"Today's Status: {donut}")
            assert donut['present'] == 9

            # Check Lists
            assert 'pending_leaves' in data['data']
            assert 'upcoming_holidays' in data['data']
            print(f"Holidays found: {len(data['data']['upcoming_holidays'])}")

            print("Rich Manager Dashboard verification PASSED.")

if __name__ == '__main__':
    try:
        mgr_id = setup_test_data()
        test_manager_rich_dashboard(mgr_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Test FAILED: {str(e)}")
    finally:
        print("Test cycle complete.")
