import sys, traceback
from app import create_app
from config import Config
from models.user import User
from models.employee import Employee
from flask import g, request

app = create_app(Config)
with app.app_context():
    with open('test_out_py.txt', 'w', encoding='utf-8') as fh:
        sys.stdout = fh
        sys.stderr = fh
        try:
            from routes.superadmin import update_employee
            class DummyUser: pass
            g.user = DummyUser()
            g.user.role = 'SUPER_ADMIN'
            g.user.id = 1
            g.user.company_id = 1
            
            with app.test_request_context(json={'company_email': 't@t.com', 'department': 'IT'}):
                res = update_employee(13)
                print('SUCCESS>', res[0].get_data(as_text=True))
        except Exception as e:
            print('ERROR>', repr(e))
            traceback.print_exc()
