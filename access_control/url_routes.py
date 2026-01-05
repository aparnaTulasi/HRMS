from flask import Blueprint

url_bp = Blueprint("url_bp", __name__)

@url_bp.route("/resolve-url")
def resolve_url():
    return {"message": "URL route working"}
