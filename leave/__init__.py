from flask import Blueprint
leave_bp = Blueprint('leave', __name__, url_prefix='/api/leaves')
from . import routes