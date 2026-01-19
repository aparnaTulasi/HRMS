from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from config import Config
from models import db


app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
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
from routes.auth import auth_bp, mail
from routes.admin import admin_bp
from routes.employee import employee_bp
from routes.superadmin import superadmin_bp
from routes.hr import hr_bp
from routes.attendance import attendance_bp
from routes.employee_advanced import employee_advanced_bp
from routes.urls import urls_bp
from routes.permissions import permissions_bp
from routes.documents import documents_bp
from routes.policies import policies_bp
from leave.routes import leave_bp
from routes.user import user_bp
from routes.otp import otp_bp
from routes.verify import verify_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
mail.init_app(app)
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(employee_bp, url_prefix='/api/employee')
app.register_blueprint(superadmin_bp, url_prefix='/api/superadmin')
app.register_blueprint(hr_bp, url_prefix='/api/hr')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
app.register_blueprint(employee_advanced_bp, url_prefix='/api/employee')
app.register_blueprint(urls_bp, url_prefix='/api/urls')
app.register_blueprint(permissions_bp, url_prefix='/api/permissions')
app.register_blueprint(documents_bp, url_prefix='/api/documents')
app.register_blueprint(policies_bp, url_prefix='/api/policies')
app.register_blueprint(leave_bp)
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(otp_bp, url_prefix='/api/otp')
app.register_blueprint(verify_bp, url_prefix='/api/verify')

@app.route('/')
def home():
    return jsonify({'message': 'HRMS API Running', 'version': '2.0'})

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     print("✅ HRMS Server Starting...")
#     app.run(debug=True, port=5000)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
