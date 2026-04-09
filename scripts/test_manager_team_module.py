import sys
import os
from datetime import datetime, date

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db
from models.user import User
from models.employee import Employee
from models.squad import Squad
from models.squad_member import SquadMember
from models.attendance import Attendance
from flask import g

def setup_test_data():
    with app.app_context():
        # Clear existing test data
        User.query.filter(User.email.like('team_test_%')).delete(synchronize_session=False)
        db.session.commit()

        # 1. Create Manager
        manager_user = User(email='team_test_mgr@example.com', role='MANAGER', status='ACTIVE', company_id=1)
        db.session.add(manager_user)
        db.session.flush()
        
        manager_emp = Employee(user_id=manager_user.id, company_id=1, full_name='Squad Manager', employee_id='SQM001')
        db.session.add(manager_emp)
        db.session.flush()

        # 2. Create Squad
        squad = Squad(company_id=1, squad_name='Alpha Team', squad_type='IT', project_name='Project Phoenix')
        db.session.add(squad)
        db.session.flush()

        # 3. Add Manager as Lead of Squad
        sm_mgr = SquadMember(squad_id=squad.id, employee_id=manager_emp.id, role='Lead')
        db.session.add(sm_mgr)

        # 4. Create Squad Members (Developers)
        for i in range(5):
            u = User(email=f'team_test_dev_{i}@example.com', role='EMPLOYEE', status='ACTIVE', company_id=1)
            db.session.add(u)
            db.session.flush()
            e = Employee(user_id=u.id, company_id=1, full_name=f'Developer {i}', employee_id=f'DEV{i:03d}')
            db.session.add(e)
            db.session.flush()
            sm = SquadMember(squad_id=squad.id, employee_id=e.id, role='Developer')
            db.session.add(sm)
            
            # Attendance for today
            att = Attendance(employee_id=e.id, attendance_date=date.today(), status='Present', company_id=1)
            db.session.add(att)

        db.session.commit()
        return manager_user.id

def test_manager_team_dashboard(manager_user_id):
    with app.app_context():
        g.user = User.query.get(manager_user_id)
        
        from routes.team_routes import get_manager_team_dashboard, get_manager_team_superstars, get_manager_team_resilience
        
        with app.test_request_context():
            g.user = User.query.get(manager_user_id)
            
            # 1. Dashboard Stats
            resp = get_manager_team_dashboard()
            data = resp.get_json()
            print(f"Dashboard Stats: {data['data']}")
            assert data['success'] is True
            assert data['data']['total_members'] == 6 # 5 devs + 1 lead
            assert data['data']['active_now'] == 5 # 5 devs present
            assert data['data']['admins_count'] == 1 # 1 lead

            # 2. Superstars
            resp = get_manager_team_superstars()
            data = resp.get_json()
            print(f"Superstars found: {len(data['data'])}")
            assert data['success'] is True
            assert len(data['data']) == 6

            # 3. Resilience
            resp = get_manager_team_resilience()
            data = resp.get_json()
            print(f"Resilience metrics: {data['data']['metrics']}")
            assert data['success'] is True
            assert 'consistency_score' in data['data']

            print("Manager 'My Team' verification PASSED.")

if __name__ == '__main__':
    try:
        mgr_id = setup_test_data()
        test_manager_team_dashboard(mgr_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Test FAILED: {str(e)}")
    finally:
        print("Test cycle complete.")
