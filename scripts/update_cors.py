import os
import sys

# Define the content for app.py with proper CORS setup
app_py_content = """
from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from config import Config
from models import db

app = Flask(__name__)
app.config.from_object(Config)

# ✅ ENABLE CORS FOR ALL ROUTES (Fixes 'Failed to fetch')
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    from models.user import User
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'message': 'Authentication required'}), 401

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
from leave.routes import leave_bp

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
app.register_blueprint(leave_bp)

@app.route('/')
def home():
    return jsonify({'message': 'HRMS API Running', 'version': '2.0'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("✅ HRMS Server Starting...")
    app.run(debug=True, port=5000)
"""

# Write to app.py in the parent directory
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app_path = os.path.join(base_dir, 'app.py')

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(app_py_content)

print(f"✅ Successfully updated {app_path} with CORS support.")