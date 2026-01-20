from flask import Blueprint, jsonify

verify_bp = Blueprint('verify', __name__)

@verify_bp.route('/', methods=['GET'])
def verify_index():
    return jsonify({"message": "Verify API is running"})