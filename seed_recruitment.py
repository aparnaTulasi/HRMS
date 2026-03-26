from app import app
from models import db
from models.job_posting import JobPosting
from models.job_applicant import JobApplicant
from models.department import Department
from datetime import date, datetime, timedelta
import random

def seed_recruitment():
    with app.app_context():
        print("Seeding recruitment data...")
        
        # 1. Clean existing (optional but helpful for fresh seed)
        JobApplicant.query.delete()
        JobPosting.query.delete()
        db.session.commit()

        # 2. Get Engineering department
        dept = Department.query.filter_by(company_id=1, department_name='Engineering').first()
        if not dept:
            dept = Department(company_id=1, department_name='Engineering', department_code='ENG')
            db.session.add(dept)
            db.session.commit()
        
        dept_id = dept.id

        # 3. Add Job Postings
        job_data = [
            ("Senior React Developer", "Full-time", "Remote", "Open"),
            ("UI/UX Designer", "Contract", "Office", "Open"),
            ("Marketing Manager", "Full-time", "Office", "Closed"),
            ("Backend Developer", "Full-time", "Hybrid", "Open")
        ]
        
        applicant_names = ["John Doe", "Mike Ross", "Sarah Wilson", "James Miller", "Elena Rodriguez", "David Chen"]
        stages = ["Applied", "Interview", "Hired", "Rejected"]

        for title, etype, loc, status in job_data:
            job = JobPosting(
                company_id=1,
                job_title=title,
                department_id=dept_id,
                employment_type=etype,
                location=loc,
                status=status,
                description="Join our fast-growing team. We are looking for talented individuals.",
                requirements="5+ years experience, Strong communication skills.",
                posted_date=date.today() - timedelta(days=random.randint(5, 30))
            )
            db.session.add(job)
            db.session.flush() # Get the job.id

            # Add applicants for THIS job
            for _ in range(random.randint(2, 6)):
                applicant = JobApplicant(
                    job_id=job.id,
                    full_name=random.choice(applicant_names),
                    email=f"candidate{random.randint(100, 999)}@example.com",
                    current_stage=random.choice(stages),
                    applied_date=date.today() - timedelta(days=random.randint(1, 4))
                )
                db.session.add(applicant)

        db.session.commit()
        print("Recruitment seeding COMPLETE!")

if __name__ == "__main__":
    seed_recruitment()
