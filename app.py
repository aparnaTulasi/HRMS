from flask import Flask, request
import logging
from datetime import timedelta
import re
from flask_cors import CORS
from models import db
from config import Config
from flask_jwt_extended import JWTManager

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.superadmin import superadmin_bp
from routes.hr import hr_bp
from routes.employee import employee_bp
from routes.attendance import attendance_bp
from routes.documents import documents_bp
from routes.user import user_bp
from routes.policies import policies_bp
from leave import leave_bp
from routes.approvals import approvals_bp
app = Flask(__name__)
app.config.from_object(Config)

# ✅ Enable Request Logging (To see if frontend is connecting)
logging.basicConfig(level=logging.DEBUG)

@app.before_request
def log_request_info():
    app.logger.info(f"📡 Incoming Request: {request.method} {request.url} | Origin: {request.headers.get('Origin')}")

app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["SESSION_PERMANENT"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)

jwt = JWTManager(app)

CORS(
    app,
    resources={r"/api/*": {
        "origins": [
            "http://localhost:5173",      # Vite
            "http://127.0.0.1:5173",
            "http://localhost:3000",      # For Create React App
            re.compile(r"^http://192\.168\..*:\d+$")  # Any local network IP on any port
        ]
    }},
    supports_credentials=True
)

db.init_app(app)

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(admin_bp, url_prefix="/api/admin")
app.register_blueprint(superadmin_bp, url_prefix="/api/superadmin")

app.register_blueprint(hr_bp, url_prefix="/api/hr")
app.register_blueprint(employee_bp, url_prefix="/api/employee")
app.register_blueprint(attendance_bp, url_prefix="/api/attendance")
app.register_blueprint(documents_bp, url_prefix="/api/documents")
app.register_blueprint(user_bp, url_prefix="/api/user")
app.register_blueprint(policies_bp, url_prefix="/api/policies")
app.register_blueprint(leave_bp)
app.register_blueprint(approvals_bp, url_prefix="/api/approvals")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
