from app import app, db
from leave.models import LeavePolicy
import json

app.app_context().push()

# Import the serialize function from routes
from leave.routes import serialize

# Get policy 1 fresh from database
policy = LeavePolicy.query.filter_by(id=1).first()
print(f"Policy from DB:")
print(f"  config_json: {policy.config_json}")

# Serialize it
serialized = serialize(policy)
print(f"\nSerialized policy:")
print(json.dumps(serialized, indent=2))

print(f"\nConfig value in serialized: {serialized.get('config', {}).get('sandwich')}")
