from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from models import db
import logging

# Force-enable Werkzeug logging
logging.basicConfig(level=logging.INFO)
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.INFO)
werkzeug_logger.disabled = False

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
db.init_app(app)

# Register Models (Ensure they are loaded for SQLAlchemy)
import models.user
import models.company
import models.employee
import models.permission
import models.attendance
import models.department
import models.filter
import models.urls
import models.payroll
import models.employee_address
import models.employee_bank
import models.employee_documents
import leave.models
import models.shift

# Import blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.employee import employee_bp
from routes.superadmin import superadmin_bp
from routes.hr import hr_bp
from routes.attendance import attendance_bp
from routes.employee_advanced import employee_advanced_bp
from routes.urls import urls_bp
from routes.permissions import permissions_bp
from routes.documents import documents_bp
from leave import leave_bp
from routes.shift import shift_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(superadmin_bp, url_prefix='/api/superadmin')
app.register_blueprint(hr_bp, url_prefix='/api/hr')
app.register_blueprint(employee_bp, url_prefix='/api/employee')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
app.register_blueprint(employee_advanced_bp, url_prefix='/api/employee')
app.register_blueprint(urls_bp, url_prefix='/api/urls')
app.register_blueprint(permissions_bp, url_prefix='/api/permissions')
app.register_blueprint(documents_bp, url_prefix='/api/documents')
app.register_blueprint(leave_bp, url_prefix="/api/leaves")
app.register_blueprint(shift_bp, url_prefix='/api/shifts')

@app.before_request
def log_request():
    print(f"➡️ {request.method} {request.path}", flush=True)

@app.route('/')
def home():
    return jsonify({'message': 'HRMS API Running', 'version': '2.0'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("✅ HRMS Server Starting...")
    app.run(host="0.0.0.0", port=5000, debug=True)