from app import app, db
from leave.models import LeavePolicy
import json

app.app_context().push()

# Get policy 1
policy = LeavePolicy.query.get(1)
print(f"Policy ID: {policy.id}")
print(f"Policy Name: {policy.name}")
print(f"Raw config_json: {policy.config_json}")
print(f"Type of config_json: {type(policy.config_json)}")

if policy.config_json:
    try:
        config = json.loads(policy.config_json)
        print(f"Parsed config: {config}")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
