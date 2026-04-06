from flask import Blueprint, jsonify, g
from utils.decorators import validate_company_url
from routes.dashboard_routes import _get_role_dashboard_stats

main_bp = Blueprint('main', __name__)

@main_bp.route("/<username>/<company>/dashboard", methods=['GET'])
@validate_company_url
def dynamic_dashboard(username, company):
    """
    Universal Dashboard Entry Point.
    URL: /<username>/<company>/dashboard
    Security: JWT required + URL Validation
    """
    # Simply call the refactored stats logic
    return _get_role_dashboard_stats()
