from flask import Blueprint, request, jsonify
from sqlalchemy import text
from models import db

# company model is in models/company.py
from models.company import Company

# --- JWT / token auth (safe) ---
import jwt
from config import Config

try:
    from models.user import User
except Exception:
    User = None

companies_bp = Blueprint("companies_bp", __name__)


def _get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.replace("Bearer ", "").strip()
    return None


def _require_super_admin():
    token = _get_bearer_token()
    if not token:
        return jsonify({"success": False, "message": "Token is missing"}), 401

    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return jsonify({"success": False, "message": "Invalid token"}), 401

    role = (payload.get("role") or "").upper()
    if role not in ["SUPER_ADMIN", "SUPERADMIN", "SUPER-ADMIN"]:
        return jsonify({"success": False, "message": "Forbidden: Super Admin only"}), 403

    return None


def _slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = "".join(ch if (ch.isalnum() or ch in ["-", " "]) else "" for ch in s)
    s = "-".join([p for p in s.split() if p])
    return (s[:50] or "company")

def _unique_subdomain(base: str) -> str:
    sub = base
    i = 2
    while Company.query.filter_by(subdomain=sub).first():
        sub = f"{base}-{i}"
        i += 1
    return sub

def _to_frontend_company(c: Company):
    # Frontend expects: name, email, address, status
    # Your DB uses: company_name, email, address. status may not exist → default "Active"
    status = getattr(c, "status", None) or "Active"
    return {
        "id": c.id,
        "name": c.company_name,
        "email": c.email,
        "address": c.address,
        "status": status
    }


@companies_bp.route("/companies", methods=["GET"])
def get_all_companies():
    guard = _require_super_admin()
    if guard:
        return guard

    items = Company.query.order_by(Company.id.desc()).all()
    return jsonify([_to_frontend_company(c) for c in items]), 200


@companies_bp.route("/companies", methods=["POST"])
def create_company():
    guard = _require_super_admin()
    if guard:
        return guard

    data = request.get_json(silent=True) or {}

    # Frontend sends: name, email, address
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    address = data.get("address")

    if not name:
        return jsonify({"success": False, "message": "Company name is required"}), 400

    # Generate unique subdomain
    subdomain = _unique_subdomain(_slugify(name))

    try:
        new_company = Company(
            company_name=name,
            subdomain=subdomain,
            email=email,
            address=address,
            status="Active",
            # Optional fields
            industry=data.get("industry"),
            company_size=data.get("company_size"),
            country=data.get("country")
        )

        db.session.add(new_company)
        db.session.commit()

        return jsonify({"success": True, "message": "Company created", "data": _to_frontend_company(new_company)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@companies_bp.route("/companies/<int:company_id>", methods=["PUT"])
def update_company(company_id):
    guard = _require_super_admin()
    if guard:
        return guard

    c = Company.query.get(company_id)
    if not c:
        return jsonify({"success": False, "message": "Company not found"}), 404

    data = request.get_json(silent=True) or {}

    # frontend sends: name/email/address
    if "name" in data:
        c.company_name = (data.get("name") or "").strip()
    if "email" in data:
        c.email = (data.get("email") or "").strip()
    if "address" in data:
        c.address = data.get("address")

    db.session.commit()
    return jsonify({"success": True, "message": "Company updated", "data": _to_frontend_company(c)}), 200


@companies_bp.route("/companies/<int:company_id>", methods=["DELETE"])
def delete_company(company_id):
    guard = _require_super_admin()
    if guard:
        return guard

    c = Company.query.get(company_id)
    if not c:
        return jsonify({"success": False, "message": "Company not found"}), 404

    # Soft delete if status column exists, else hard delete
    if hasattr(c, "status"):
        c.status = "Inactive"
        db.session.commit()
        return jsonify({"success": True, "message": "Company deactivated"}), 200

    # If no status column in DB, do hard delete (not recommended, but avoids errors)
    db.session.delete(c)
    db.session.commit()
    return jsonify({"success": True, "message": "Company deleted"}), 200