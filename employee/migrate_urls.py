import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models.master import db
from models.system_urls import SystemUrl, RoleUrlPermission

def migrate():
    with app.app_context():
        print("🔄 Migrating URL permission tables...")

        try:
            RoleUrlPermission.__table__.drop(db.engine)
            print("✅ Dropped role_url_permissions table")
        except Exception as e:
            print("ℹ role_url_permissions table not found")

        try:
            SystemUrl.__table__.drop(db.engine)
            print("✅ Dropped system_urls table")
        except Exception as e:
            print("ℹ system_urls table not found")

        db.create_all()
        print("✅ Tables recreated successfully (NO seed data)")

if __name__ == "__main__":
    migrate()