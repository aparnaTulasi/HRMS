from flask import Blueprint
from utils.responses import ok

stabilization_bp = Blueprint("stabilization", __name__)

@stabilization_bp.route("/api/health", methods=["GET"])
def health():
    return ok("HRMS is healthy", data={"status": "up"})