from datetime import datetime
from flask import Blueprint, request, jsonify, g
from sqlalchemy import or_

from models import db
from models.asset import Asset, AssetAllocation, AssetConditionLog

assets_bp = Blueprint("assets_bp", __name__)

# ---------- Optional auth imports (won't break if not present) ----------
def _no_auth(fn):
    return fn

try:
    # If your project has something like these, it will use it
    from utils.auth import token_required  # type: ignore
except Exception:
    token_required = _no_auth

# ---------------- Helpers ----------------
def _json_error(msg, code=400):
    return jsonify({"success": False, "message": msg}), code

def _asset_to_dict(a: Asset):
    return {
        "id": a.id,
        "company_id": a.company_id,
        "asset_code": a.asset_code,
        "asset_name": a.asset_name,
        "category": a.category,
        "serial_number": a.serial_number,
        "brand": a.brand,
        "model": a.model,
        "vendor_name": a.vendor_name,
        "purchase_date": a.purchase_date.isoformat() if a.purchase_date else None,
        "purchase_cost": a.purchase_cost,
        "warranty_end_date": a.warranty_end_date.isoformat() if a.warranty_end_date else None,
        "location": a.location,
        "notes": a.notes,
        "status": a.status,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }

def _allocation_to_dict(x: AssetAllocation):
    return {
        "id": x.id,
        "asset_id": x.asset_id,
        "employee_id": x.employee_id,
        "company_id": x.company_id,
        "allocation_date": x.allocation_date.isoformat() if x.allocation_date else None,
        "expected_return_date": x.expected_return_date.isoformat() if x.expected_return_date else None,
        "return_date": x.return_date.isoformat() if x.return_date else None,
        "issue_notes": x.issue_notes,
        "return_notes": x.return_notes,
        "issued_by": x.issued_by,
        "returned_by": x.returned_by,
        "status": x.status,
    }

def _log_to_dict(l: AssetConditionLog):
    return {
        "id": l.id,
        "asset_id": l.asset_id,
        "company_id": l.company_id,
        "log_type": l.log_type,
        "condition": l.condition,
        "notes": l.notes,
        "logged_by": l.logged_by,
        "logged_at": l.logged_at.isoformat() if l.logged_at else None,
    }

# =========================================================
#  A) ASSET MASTER APIs
# =========================================================

@assets_bp.route("", methods=["POST"])
@token_required
def create_asset():
    data = request.get_json(silent=True) or {}

    company_id = data.get("company_id")
    asset_code = data.get("asset_code")
    asset_name = data.get("asset_name")

    if not company_id or not asset_code or not asset_name:
        return _json_error("company_id, asset_code, asset_name are required")

    # Prevent duplicate asset_code
    if Asset.query.filter_by(asset_code=asset_code).first():
        return _json_error("asset_code already exists", 409)

    a = Asset(
        company_id=company_id,
        asset_code=asset_code,
        asset_name=asset_name,
        category=data.get("category"),
        serial_number=data.get("serial_number"),
        brand=data.get("brand"),
        model=data.get("model"),
        vendor_name=data.get("vendor_name"),
        location=data.get("location"),
        notes=data.get("notes"),
        status=data.get("status") or "Available",
        is_active=True,
    )

    # Optional dates
    if data.get("purchase_date"):
        a.purchase_date = datetime.strptime(data["purchase_date"], "%Y-%m-%d").date()
    if data.get("warranty_end_date"):
        a.warranty_end_date = datetime.strptime(data["warranty_end_date"], "%Y-%m-%d").date()

    if data.get("purchase_cost") is not None:
        a.purchase_cost = float(data["purchase_cost"])

    db.session.add(a)
    db.session.commit()
    return jsonify({"success": True, "data": _asset_to_dict(a)}), 201


@assets_bp.route("/bulk-upload", methods=["POST"])
@token_required
def bulk_create_assets():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("Request body must be a JSON object", 400)
    assets_to_create = data.get("assets")

    if not isinstance(assets_to_create, list):
        return _json_error("Request body must be a JSON object with an 'assets' key containing a list.", 400)

    created_assets = []
    errors = []

    for i, asset_data in enumerate(assets_to_create):
        company_id = asset_data.get("company_id")
        asset_code = asset_data.get("asset_code")
        asset_name = asset_data.get("asset_name")

        if not company_id or not asset_code or not asset_name:
            errors.append({"index": i, "error": "company_id, asset_code, and asset_name are required"})
            continue

        if Asset.query.filter_by(asset_code=asset_code, company_id=company_id).first():
            errors.append({"index": i, "asset_code": asset_code, "error": "asset_code already exists for this company"})
            continue

        a = Asset(
            company_id=company_id,
            asset_code=asset_code,
            asset_name=asset_name,
            category=asset_data.get("category"),
            serial_number=asset_data.get("serial_number"),
            brand=asset_data.get("brand"),
            model=asset_data.get("model"),
            vendor_name=asset_data.get("vendor_name"),
            location=asset_data.get("location"),
            notes=asset_data.get("notes"),
            status=asset_data.get("status") or "Available",
            is_active=True,
        )

        if asset_data.get("purchase_date"):
            a.purchase_date = datetime.strptime(asset_data["purchase_date"], "%Y-%m-%d").date()
        if asset_data.get("warranty_end_date"):
            a.warranty_end_date = datetime.strptime(asset_data["warranty_end_date"], "%Y-%m-%d").date()
        if asset_data.get("purchase_cost") is not None:
            a.purchase_cost = float(asset_data["purchase_cost"])

        db.session.add(a)
        created_assets.append(a)

    if errors:
        db.session.rollback()
        return jsonify({"success": False, "message": "Errors occurred during bulk upload. No assets were saved.", "errors": errors}), 400

    db.session.commit()
    # We need to refresh the objects to get default values like created_at
    for a in created_assets:
        db.session.refresh(a)

    return jsonify({"success": True, "message": f"Successfully created {len(created_assets)} assets.", "data": [_asset_to_dict(a) for a in created_assets]}), 201


@assets_bp.route("", methods=["GET"])
@assets_bp.route("/search", methods=["GET"])
@token_required
def list_assets():
    args = request.args
    company_id = args.get("company_id", type=int)
    status = args.get("status")
    category = args.get("category")
    brand = args.get("brand")
    location = args.get("location")
    q = args.get("q")  # generic search

    query = Asset.query.filter(Asset.is_active == True)

    if company_id:
        query = query.filter(Asset.company_id == company_id)
    if status:
        query = query.filter(Asset.status == status)
    if category:
        query = query.filter(Asset.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(Asset.brand.ilike(f"%{brand}%"))
    if location:
        query = query.filter(Asset.location.ilike(f"%{location}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Asset.asset_code.ilike(like),
            Asset.asset_name.ilike(like),
            Asset.serial_number.ilike(like),
            Asset.model.ilike(like)
        ))

    assets = query.order_by(Asset.id.desc()).all()
    return jsonify({"success": True, "count": len(assets), "data": [_asset_to_dict(a) for a in assets]}), 200


@assets_bp.route("/stats", methods=["GET"])
@token_required
def asset_stats():
    company_id = request.args.get("company_id", type=int)
    
    # Base query for active assets
    base_query = Asset.query.filter(Asset.is_active == True)
    if company_id:
        base_query = base_query.filter(Asset.company_id == company_id)

    # 1. Status Counts
    # Initialize default statuses with 0
    stats = {s: 0 for s in ["Available", "Assigned", "Damaged", "Retired", "Repair"]}
    
    status_counts = db.session.query(Asset.status, db.func.count(Asset.id))\
        .filter(Asset.is_active == True)
    
    if company_id:
        status_counts = status_counts.filter(Asset.company_id == company_id)
        
    status_counts = status_counts.group_by(Asset.status).all()

    total_assets = 0
    for status, count in status_counts:
        stats[status] = count
        total_assets += count
    
    stats["Total"] = total_assets

    # 2. Category Counts
    cat_query = db.session.query(Asset.category, db.func.count(Asset.id)).filter(Asset.is_active == True)
    if company_id:
        cat_query = cat_query.filter(Asset.company_id == company_id)
    
    cat_counts = cat_query.group_by(Asset.category).all()
    categories = {c: count for c, count in cat_counts if c}

    return jsonify({
        "success": True,
        "stats": stats,
        "categories": categories
    }), 200


@assets_bp.route("/<int:asset_id>", methods=["GET"])
@token_required
def get_asset(asset_id):
    a = Asset.query.get(asset_id)
    if not a or not a.is_active:
        return _json_error("Asset not found", 404)
    return jsonify({"success": True, "data": _asset_to_dict(a)}), 200


@assets_bp.route("/<int:asset_id>", methods=["PUT"])
@token_required
def update_asset(asset_id):
    a = Asset.query.get(asset_id)
    if not a or not a.is_active:
        return _json_error("Asset not found", 404)

    data = request.get_json(silent=True) or {}

    # Updatable fields
    for field in ["asset_name", "category", "serial_number", "brand", "model", "vendor_name", "location", "notes", "status"]:
        if field in data:
            setattr(a, field, data.get(field))

    if "purchase_cost" in data and data["purchase_cost"] is not None:
        a.purchase_cost = float(data["purchase_cost"])

    if data.get("purchase_date"):
        a.purchase_date = datetime.strptime(data["purchase_date"], "%Y-%m-%d").date()
    if data.get("warranty_end_date"):
        a.warranty_end_date = datetime.strptime(data["warranty_end_date"], "%Y-%m-%d").date()

    db.session.commit()
    return jsonify({"success": True, "data": _asset_to_dict(a)}), 200


@assets_bp.route("/<int:asset_id>", methods=["DELETE"])
@token_required
def deactivate_asset(asset_id):
    a = Asset.query.get(asset_id)
    if not a or not a.is_active:
        return _json_error("Asset not found", 404)

    # Soft delete
    a.is_active = False
    db.session.commit()
    return jsonify({"success": True, "message": "Asset deactivated"}), 200


# =========================================================
#  B) ISSUE / RETURN WORKFLOWS
# =========================================================

@assets_bp.route("/<int:asset_id>/issue", methods=["POST"])
@token_required
def issue_asset(asset_id):
    a = Asset.query.get(asset_id)
    if not a or not a.is_active:
        return _json_error("Asset not found", 404)

    if a.status != "Available":
        return _json_error(f"Asset is not available (current status: {a.status})", 409)

    data = request.get_json(silent=True) or {}
    employee_id = data.get("employee_id")
    company_id = data.get("company_id") or a.company_id

    if not employee_id:
        return _json_error("employee_id is required")

    alloc = AssetAllocation(
        asset_id=a.id,
        employee_id=employee_id,
        company_id=company_id,
        issue_notes=data.get("issue_notes"),
        issued_by=data.get("issued_by"),
        status="Assigned",
    )

    if data.get("allocation_date"):
        alloc.allocation_date = datetime.strptime(data["allocation_date"], "%Y-%m-%d").date()
    if data.get("expected_return_date"):
        alloc.expected_return_date = datetime.strptime(data["expected_return_date"], "%Y-%m-%d").date()

    # Update asset status
    a.status = "Assigned"

    db.session.add(alloc)
    db.session.commit()
    return jsonify({"success": True, "data": _allocation_to_dict(alloc)}), 201


@assets_bp.route("/<int:asset_id>/transfer", methods=["POST"])
@token_required
def transfer_asset(asset_id):
    a = Asset.query.get(asset_id)
    if not a or not a.is_active:
        return _json_error("Asset not found", 404)

    data = request.get_json(silent=True) or {}
    from_emp_id = data.get("from_employee_id")
    to_emp_id = data.get("to_employee_id")
    
    if not from_emp_id or not to_emp_id:
        return _json_error("from_employee_id and to_employee_id are required")
        
    # 1. Verify current assignment
    current_alloc = AssetAllocation.query.filter_by(
        asset_id=asset_id,
        employee_id=from_emp_id,
        status='Assigned'
    ).order_by(AssetAllocation.id.desc()).first()
    
    if not current_alloc:
        return _json_error("Asset is not currently assigned to the source employee", 400)
        
    # 2. Return from old employee
    current_alloc.status = 'Returned'
    current_alloc.return_date = datetime.utcnow().date()
    current_alloc.return_notes = f"Transferred to employee ID {to_emp_id}"
    current_alloc.returned_by = g.user.id if hasattr(g, 'user') and g.user else None
    
    # 3. Issue to new employee
    new_alloc = AssetAllocation(
        asset_id=asset_id,
        employee_id=to_emp_id,
        company_id=a.company_id,
        allocation_date=datetime.utcnow().date(),
        status='Assigned',
        issue_notes=f"Transferred from employee ID {from_emp_id}",
        issued_by=g.user.id if hasattr(g, 'user') and g.user else None
    )
    
    # Asset status remains Assigned
    a.status = "Assigned"
    
    db.session.add(new_alloc)
    db.session.commit()
    
    return jsonify({
        "success": True, 
        "message": "Asset transferred successfully",
        "data": _allocation_to_dict(new_alloc)
    }), 200


@assets_bp.route("/allocations/<int:allocation_id>/return", methods=["POST"])
@token_required
def return_asset(allocation_id):
    alloc = AssetAllocation.query.get(allocation_id)
    if not alloc:
        return _json_error("Allocation not found", 404)

    if alloc.status != "Assigned":
        return _json_error(f"Allocation already {alloc.status}", 409)

    data = request.get_json(silent=True) or {}

    alloc.return_notes = data.get("return_notes")
    alloc.returned_by = data.get("returned_by")
    alloc.status = "Returned"
    alloc.return_date = datetime.strptime(data["return_date"], "%Y-%m-%d").date() if data.get("return_date") else datetime.utcnow().date()

    a = Asset.query.get(alloc.asset_id)
    if a and a.is_active:
        # If returned damaged, keep Damaged else Available
        new_status = data.get("asset_status_after_return") or "Available"
        a.status = new_status

    db.session.commit()
    return jsonify({"success": True, "data": _allocation_to_dict(alloc)}), 200


@assets_bp.route("/allocations", methods=["GET"])
@token_required
def list_allocations():
    company_id = request.args.get("company_id", type=int)
    employee_id = request.args.get("employee_id", type=int)
    status = request.args.get("status")  # Assigned/Returned

    query = AssetAllocation.query
    if company_id:
        query = query.filter(AssetAllocation.company_id == company_id)
    if employee_id:
        query = query.filter(AssetAllocation.employee_id == employee_id)
    if status:
        query = query.filter(AssetAllocation.status == status)

    rows = query.order_by(AssetAllocation.id.desc()).all()
    return jsonify({"success": True, "count": len(rows), "data": [_allocation_to_dict(r) for r in rows]}), 200


@assets_bp.route("/by-employee/<int:employee_id>", methods=["GET"])
@token_required
def assets_by_employee(employee_id):
    # Current assigned assets for an employee
    rows = AssetAllocation.query.filter_by(employee_id=employee_id, status="Assigned").order_by(AssetAllocation.id.desc()).all()
    return jsonify({"success": True, "count": len(rows), "data": [_allocation_to_dict(r) for r in rows]}), 200


# =========================================================
#  C) DAMAGE / CONDITION LOGS
# =========================================================

@assets_bp.route("/<int:asset_id>/condition-logs", methods=["POST"])
@token_required
def add_condition_log(asset_id):
    a = Asset.query.get(asset_id)
    if not a or not a.is_active:
        return _json_error("Asset not found", 404)

    data = request.get_json(silent=True) or {}
    if not data.get("log_type"):
        return _json_error("log_type is required (Damage/Repair/Inspection)")

    log = AssetConditionLog(
        asset_id=a.id,
        company_id=data.get("company_id") or a.company_id,
        log_type=data["log_type"],
        condition=data.get("condition"),
        notes=data.get("notes"),
        logged_by=data.get("logged_by"),
    )

    # If damage log, optionally mark asset Damaged
    if data.get("mark_asset_damaged") is True:
        a.status = "Damaged"

    db.session.add(log)
    db.session.commit()
    return jsonify({"success": True, "data": _log_to_dict(log)}), 201


@assets_bp.route("/<int:asset_id>/condition-logs", methods=["GET"])
@token_required
def list_condition_logs(asset_id):
    a = Asset.query.get(asset_id)
    if not a or not a.is_active:
        return _json_error("Asset not found", 404)

    logs = AssetConditionLog.query.filter_by(asset_id=a.id).order_by(AssetConditionLog.id.desc()).all()
    return jsonify({"success": True, "count": len(logs), "data": [_log_to_dict(l) for l in logs]}), 200
