from employee.employee_routes import employee_bp
from employee.employee_documents import employee_documents_bp

def register_employee_routes(app):
    app.register_blueprint(employee_bp)
    app.register_blueprint(employee_documents_bp)
