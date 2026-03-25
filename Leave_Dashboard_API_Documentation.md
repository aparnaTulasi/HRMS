# Leave Management Control Dashboard API Documentation

This document describes the APIs for the Leave Management Control dashboard for Super Admin, Admin, and HR roles.

## 1. Dashboard Overview
**Endpoint**: `GET /api/leaves/dashboard/summary`
**Description**: Returns overall counts, entitlement progress data, and leave type distribution for charts.

**Response Structure**:
```json
{
  "counts": { "total_balance": 12.0, "pending": 3, "approved": 8, "rejected": 1 },
  "entitlements": [
    { "type": "Casual Leave", "code": "CL", "used": 3.0, "total": 10.0, "color": "blue" }
  ],
  "distribution": [
    { "name": "CL", "value": 3.0 },
    { "name": "Remaining", "value": 2.0 }
  ]
}
```

## 2. Pending Approvals Tab
**Endpoint**: `GET /api/leaves/pending-approvals`
**Description**: Detailed list of pending requests for the company. Use this for the "Pending" tab and "Bulk Approval" tab.

**Response Fields**: `employee_name`, `dept`, `leave_type_name`, `from_date`, `to_date`, `days`, `reason`, `applied`, `status`.

## 3. Bulk Approval Actions
**Endpoint**: `POST /api/leaves/bulk-action`
**Description**: Approve or reject multiple leave requests at once.

**Request Payload**:
```json
{
  "ids": [101, 102],
  "action": "APPROVE" 
}
```

## 4. Leave Policies Tab
**Endpoints**:
- **List All**: `GET /api/leaves/ui-policies`
- **Create**: `POST /api/leaves/ui-policies`
- **Update**: `PUT /api/leaves/ui-policies/<id>`
- **Delete**: `DELETE /api/leaves/ui-policies/<id>`

**Create/Update Payload Example**:
```json
{
  "name": "Sick Leave",
  "days": 12,
  "carryForward": true,
  "maxCarryForward": 5
}
```

## 5. History Log Tab
**Endpoint**: `GET /api/leaves/history`
**Description**: returns comprehensive leave history with filters for status, type, and dates.

**Response Fields**: `id`, `employee_name`, `leave_type`, `from_date`, `to_date`, `days`, `status`, `approved_by` (Approver Name), `applied_on`.

---

### Individual Actions (OK / No Buttons)
- **Approve**: `POST /api/leaves/<id>/approve`
- **Reject/Action**: `PUT /api/leaves/<id>/action` (Payload: `{"action": "REJECT"}`)
