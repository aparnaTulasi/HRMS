# routes/desk_routes.py
from flask import Blueprint, request, jsonify, g
from datetime import datetime, date
from models import db
from models.desk import Desk, DeskBooking
from models.employee import Employee
from utils.decorators import token_required, permission_required
from constants.permissions_registry import Permissions
from sqlalchemy import desc, func, and_
from utils.date_utils import parse_date

desk_bp = Blueprint('desk', __name__)

@desk_bp.route('/stats', methods=['GET'])
@token_required
@permission_required(Permissions.DESK_VIEW)
def get_desk_stats():
    """
    Summary counts for the desk management dashboard.
    """
    cid = g.user.company_id
    today = date.today()
    
    total_desks = Desk.query.filter_by(company_id=cid).count()
    
    # Available now: Status is Available AND no active booking for today
    booked_today_ids = db.session.query(DeskBooking.desk_id).filter(
        DeskBooking.company_id == cid,
        DeskBooking.booking_date == today,
        DeskBooking.status != 'Cancelled'
    ).subquery()
    
    available_now = Desk.query.filter(
        Desk.company_id == cid,
        Desk.status == 'Available',
        ~Desk.id.in_(booked_today_ids)
    ).count()
    
    todays_bookings = DeskBooking.query.filter(
        DeskBooking.company_id == cid,
        DeskBooking.booking_date == today,
        DeskBooking.status != 'Cancelled'
    ).count()
    
    permanent_seats = Desk.query.filter_by(company_id=cid, is_permanent=True).count()
    
    return jsonify({
        "success": True,
        "data": {
            "total_desks": total_desks,
            "available_now": available_now,
            "todays_bookings": todays_bookings,
            "permanent_seats": permanent_seats
        }
    })

@desk_bp.route('/list', methods=['GET'])
@token_required
@permission_required(Permissions.DESK_VIEW)
def list_desks():
    """
    Lists all desks with their live status.
    """
    cid = g.user.company_id
    today = date.today()
    
    # Get all desks
    desks = Desk.query.filter_by(company_id=cid).order_by(Desk.desk_code).all()
    
    # Get active bookings for today to determine live status
    bookings_today = {b.desk_id: b for b in DeskBooking.query.filter(
        DeskBooking.company_id == cid,
        DeskBooking.booking_date == today,
        DeskBooking.status != 'Cancelled'
    ).all()}
    
    output = []
    for d in desks:
        # Determine live status: Assigned (if permanent), Booked (if booking found), or Available
        current_status = d.status
        if d.is_permanent:
            current_status = 'Assigned'
        elif d.id in bookings_today:
            current_status = 'Booked'
        else:
            current_status = 'Available'
            
        output.append({
            "id": d.id,
            "desk_id": d.desk_code,
            "location": d.location,
            "floor": d.floor,
            "wing": d.wing,
            "team": d.team,
            "is_permanent": d.is_permanent,
            "status": current_status
        })
        
    return jsonify({"success": True, "data": output}), 200

@desk_bp.route('/occupancy', methods=['GET'])
@token_required
@permission_required(Permissions.DESK_VIEW)
def get_occupancy():
    """
    Floor-wise occupancy breakdown.
    """
    cid = g.user.company_id
    today = date.today()
    
    # Group desks by floor
    floors = db.session.query(Desk.floor, func.count(Desk.id)).filter_by(company_id=cid).group_by(Desk.floor).all()
    
    # Get occupied counts per floor
    # Occupied if permanent OR has booking today
    booked_today_ids = db.session.query(DeskBooking.desk_id).filter(
        DeskBooking.company_id == cid,
        DeskBooking.booking_date == today,
        DeskBooking.status != 'Cancelled'
    ).subquery()
    
    occupied_per_floor = db.session.query(Desk.floor, func.count(Desk.id)).filter(
        Desk.company_id == cid,
        (Desk.is_permanent == True) | (Desk.id.in_(booked_today_ids))
    ).group_by(Desk.floor).all()
    
    occupied_map = {f: count for f, count in occupied_per_floor}
    
    output = []
    for floor_name, total_count in floors:
        occ_count = occupied_map.get(floor_name, 0)
        output.append({
            "floor": floor_name,
            "occupied": occ_count,
            "total": total_count,
            "percentage": round((occ_count / total_count * 100), 1) if total_count > 0 else 0
        })
        
    return jsonify({"success": True, "data": output}), 200

@desk_bp.route('/book', methods=['POST'])
@token_required
@permission_required(Permissions.DESK_BOOK)
def book_desk():
    """
    Creates a new desk reservation.
    """
    data = request.get_json()
    desk_id = data.get('desk_id') # This is the DB integer ID
    booking_date_str = data.get('booking_date') # "06-04-2026"
    preferred_time = data.get('preferred_time', "09:00 AM")
    
    if not desk_id or not booking_date_str:
        return jsonify({"success": False, "message": "Desk and Date are required"}), 400
        
    try:
        b_date = parse_date(booking_date_str)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
        
    # Check if desk exists
    desk = Desk.query.filter_by(id=desk_id, company_id=g.user.company_id).first()
    if not desk:
        return jsonify({"success": False, "message": "Desk not found"}), 404
        
    if desk.is_permanent:
        return jsonify({"success": False, "message": "This desk is a permanent seat and cannot be booked"}), 400
        
    # Check if already booked for that date
    existing_booking = DeskBooking.query.filter(
        DeskBooking.desk_id == desk_id,
        DeskBooking.booking_date == b_date,
        DeskBooking.status != 'Cancelled'
    ).first()
    
    if existing_booking:
        return jsonify({"success": False, "message": "Desk is already booked for this date"}), 400
        
    # Check if user already has a booking for that date
    if not g.user.employee_profile:
        return jsonify({"success": False, "message": "Employee profile not found"}), 404
        
    user_booking = DeskBooking.query.filter(
        DeskBooking.employee_id == g.user.employee_profile.id,
        DeskBooking.booking_date == b_date,
        DeskBooking.status != 'Cancelled'
    ).first()
    
    if user_booking:
        return jsonify({"success": False, "message": f"You already have a desk booked for {booking_date_str}"}), 400

    new_booking = DeskBooking(
        company_id=g.user.company_id,
        desk_id=desk_id,
        employee_id=g.user.employee_profile.id,
        booking_date=b_date,
        preferred_time=preferred_time,
        status='Confirmed'
    )
    
    db.session.add(new_booking)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Desk booked successfully", "booking_id": new_booking.id}), 201

@desk_bp.route('/my-bookings', methods=['GET'])
@token_required
def my_bookings():
    """
    List bookings for the logged-in employee.
    """
    if not g.user.employee_profile:
         return jsonify({"success": True, "data": []}), 200
         
    bookings = DeskBooking.query.filter_by(
        employee_id=g.user.employee_profile.id,
        company_id=g.user.company_id
    ).order_by(desc(DeskBooking.booking_date)).all()
    
    output = []
    for b in bookings:
        output.append({
            "id": b.id,
            "booking_id": f"B{b.id:03d}",
            "desk_code": b.desk.desk_code,
            "employee_name": g.user.name,
            "date": b.booking_date.strftime("%Y-%m-%d"),
            "time": b.preferred_time,
            "status": b.status
        })
        
    return jsonify({"success": True, "data": output}), 200
