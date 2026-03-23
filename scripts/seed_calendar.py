import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db
from models.calendar_event import CalendarEvent
from datetime import datetime

def seed_calendar_events():
    with app.app_context():
        if CalendarEvent.query.count() > 0:
            print("Events already exist. Skipping seed.")
            return

        print("Seeding calendar events...")
        events = [
            {
                "title": "Dentist Appointment",
                "date": "2026-03-21",
                "start_time": "09:30",
                "end_time": "10:30",
                "type": "personal",
                "description": "Regular checkup",
                "company_id": 1,
                "created_by": 1
            },
            {
                "title": "Team Meeting",
                "date": "2026-03-21",
                "start_time": "11:00",
                "end_time": "12:00",
                "type": "work",
                "description": "Weekly sync",
                "company_id": 1,
                "created_by": 1
            },
            {
                "title": "Project Review",
                "date": "2026-03-23",
                "start_time": "14:00",
                "end_time": "15:00",
                "type": "important",
                "description": "Critical milestone review",
                "company_id": 1,
                "created_by": 1
            }
        ]

        for e in events:
            date_obj = datetime.strptime(e['date'], '%Y-%m-%d').date()
            new_ev = CalendarEvent(
                title=e['title'],
                date=date_obj,
                start_time=e['start_time'],
                end_time=e['end_time'],
                type=e['type'],
                description=e['description'],
                company_id=e['company_id'],
                created_by=e['created_by']
            )
            db.session.add(new_ev)
        
        db.session.commit()
        print("Calendar events seeded successfully!")

if __name__ == '__main__':
    seed_calendar_events()
