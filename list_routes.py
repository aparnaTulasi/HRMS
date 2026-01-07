# list_routes.py
from app import app

print("📋 ALL REGISTERED ROUTES:")
print("="*50)

for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        methods = ','.join(rule.methods - {'OPTIONS', 'HEAD'})
        print(f"{rule.rule:50} {methods:20} {rule.endpoint}")

print("\nSuper Admin routes should include:")
print("- /api/superadmin/create-company")
print("- /api/superadmin/companies")
print("- /api/superadmin/company/<id>")