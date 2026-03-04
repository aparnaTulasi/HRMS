from app import app, db
from leave.models import LeavePolicy
import json

app.app_context().push()

# Get policy 1
policy = LeavePolicy.query.get(1)
print(f"Before update:")
print(f"  config_json: {policy.config_json}")

# Simulate the update logic
data = {"config": {"sandwich": False}}
current_config = {}
if policy.config_json:
    try:
        current_config = json.loads(policy.config_json)
    except (json.JSONDecodeError, TypeError):
        current_config = {}

print(f"  Current config after load: {current_config}")

if isinstance(data['config'], dict):
    current_config.update(data['config'])
    
print(f"  Updated config: {current_config}")
policy.config_json = json.dumps(current_config)
print(f"  config_json after json.dumps: {policy.config_json}")

db.session.commit()
print(f"\nAfter commit:")

# Re-query to verify
policy2 = LeavePolicy.query.get(1)
print(f"  config_json from DB: {policy2.config_json}")
config_parsed = json.loads(policy2.config_json)
print(f"  Parsed: {config_parsed}")
