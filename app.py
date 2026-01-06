# c:\Users\DELL5410\Desktop\HRMS\app.py
from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
from auth.routes import auth_bp
from admin.routes import admin_bp
from employee.routes import employee_bp
from superadmin.routes import superadmin_bp
from hr.routes import hr_bp

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
db.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(superadmin_bp, url_prefix='/api/superadmin')
app.register_blueprint(hr_bp, url_prefix='/api/hr')
app.register_blueprint(employee_bp, url_prefix='/api/employee')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
