# Profile Update Constants

ALLOWED_PROFILE_FIELDS = {
    "Employee": [
        "full_name",
        "phone_number",
        "gender",
        "date_of_birth",
        "bio",
        "emergency_contact"
    ],
    "EmployeeAddress": [
        "address_line1",
        "address_line2",
        "city",
        "state",
        "zip_code",
        "country"
    ],
    "SuperAdmin": [
        "first_name",
        "last_name",
        "phone_number",
        "gender",
        "date_of_birth",
        "address",
        "designation",
        "department",
        "bio",
        "emergency_contact"
    ]
}

# Display names for fields
FIELD_DISPLAY_NAMES = {
    "full_name": "Full Name",
    "phone_number": "Phone Number",
    "gender": "Gender",
    "date_of_birth": "Date of Birth",
    "bio": "Bio",
    "emergency_contact": "Emergency Contact",
    "address_line1": "Address Line 1",
    "address_line2": "Address Line 2",
    "city": "City",
    "state": "State",
    "zip_code": "Zip Code",
    "country": "Country",
    "first_name": "First Name",
    "last_name": "Last Name",
    "designation": "Designation",
    "department": "Department",
    "address": "Address"
}

ROLE_ESCALATION = {
    "EMPLOYEE": "HR",
    "HR": "ADMIN",
    "ADMIN": "SUPER_ADMIN",
    "SUPER_ADMIN": "ROOT_ADMIN"
}
