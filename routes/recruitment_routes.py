from flask import Blueprint, jsonify, request, g
from models import db
from models.job_posting import JobPosting
from models.job_applicant import JobApplicant
from models.department import Department
from utils.decorators import token_required
from datetime import date, datetime
from sqlalchemy import func

recruit_bp = Blueprint('recruitment', __name__)

@recruit_bp.route('/api/recruitment/stats', methods=['GET'])
@token_required
def get_recruitment_stats():
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 1, type=int)

    # 1. Open Positions
    open_positions = JobPosting.query.filter_by(company_id=company_id, status='Open').count()

    # 2. Total Applicants
    total_applicants = db.session.query(func.count(JobApplicant.id)).join(JobPosting).filter(JobPosting.company_id == company_id).scalar() or 0

    # 3. In Interview
    in_interview = db.session.query(func.count(JobApplicant.id)).join(JobPosting).filter(
        JobPosting.company_id == company_id,
        JobApplicant.current_stage == 'Interview'
    ).scalar() or 0

    # 4. Offers Made
    offers_made = db.session.query(func.count(JobApplicant.id)).join(JobPosting).filter(
        JobPosting.company_id == company_id,
        JobApplicant.current_stage == 'Hired' # Or add an 'Offer' stage if needed
    ).scalar() or 0

    return jsonify({
        "success": True,
        "data": {
            "open_positions": open_positions,
            "total_applicants": total_applicants,
            "in_interview": in_interview,
            "offers_made": offers_made
        }
    })

@recruit_bp.route('/api/recruitment/jobs', methods=['GET'])
@token_required
def get_jobs():
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = request.args.get('company_id', 1, type=int)

    search = request.args.get('search', '')
    status = request.args.get('status', 'Open')

    query = JobPosting.query.filter_by(company_id=company_id)
    if search:
        query = query.filter(JobPosting.job_title.ilike(f"%{search}%"))
    if status != 'All':
        query = query.filter_by(status=status)

    jobs = query.order_by(JobPosting.created_at.desc()).all()

    return jsonify({
        "success": True,
        "data": [job.to_dict() for job in jobs]
    })

@recruit_bp.route('/api/recruitment/jobs', methods=['POST'])
@token_required
def post_job():
    data = request.get_json()
    company_id = g.user.company_id
    if company_id is None and g.user.role == 'SUPER_ADMIN':
        company_id = data.get('company_id', 1)

    job_id = data.get('id')
    if job_id:
        # Update existing
        job = JobPosting.query.get(job_id)
        if not job or job.company_id != company_id:
            return jsonify({"success": False, "message": "Job not found"}), 404
    else:
        # Create new
        job = JobPosting(company_id=company_id)
    
    job.job_title = data.get('job_title')
    job.department_id = data.get('department_id')
    job.employment_type = data.get('employment_type', 'Full-time')
    job.location = data.get('location', 'Remote')
    job.description = data.get('description')
    job.requirements = data.get('requirements')
    job.status = data.get('status', 'Open')
    
    if not job_id:
        db.session.add(job)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Job posting saved successfully",
        "data": job.to_dict()
    })

@recruit_bp.route('/api/recruitment/jobs/<int:job_id>', methods=['DELETE'])
@token_required
def delete_job(job_id):
    job = JobPosting.query.get(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job not found"}), 404
    
    db.session.delete(job)
    db.session.commit()
    return jsonify({"success": True, "message": "Job posting deleted"})

@recruit_bp.route('/api/recruitment/jobs/<int:job_id>/applicants', methods=['GET'])
@token_required
def get_job_applicants(job_id):
    applicants = JobApplicant.query.filter_by(job_id=job_id).all()
    return jsonify({
        "success": True,
        "data": [a.to_dict() for a in applicants]
    })

@recruit_bp.route('/api/recruitment/applicants/<int:app_id>/status', methods=['PATCH'])
@token_required
def update_applicant_status(app_id):
    data = request.get_json()
    applicant = JobApplicant.query.get(app_id)
    if not applicant:
        return jsonify({"success": False, "message": "Applicant not found"}), 404
    
    applicant.current_stage = data.get('status')
    db.session.commit()
    return jsonify({"success": True, "message": "Status updated"})
