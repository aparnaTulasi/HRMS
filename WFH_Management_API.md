# WFH Management API Documentation

**Base URL**: `/api/wfh`

## 1. Dashboard Statistics
- **Endpoint**: `GET /api/wfh/summary`
- **Description**: Returns counts for Total, Pending, Approved, and Rejected WFH requests.
- **Context-Aware**: Employees see their own stats; Management see company stats.
- **Response**:
```json
{
  "success": true,
  "data": {
    "total_wfh": 12,
    "pending": 2,
    "approved": 8,
    "rejected": 2
  }
}
```

## 2. WFH Requests Log (Table)
- **Endpoint**: `GET /api/wfh/requests`
- **Query Params**: `status` (All/Pending/Approved/Rejected), `search` (Search by Name/Dept)
- **Description**: Lists WFH requests with period and reason. Employees see their own history.
- **Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "employee_name": "John Doe",
      "department": "Engineering",
      "period": "2026-06-01 - 2026-06-05",
      "days": 5,
      "reason": "Medical Emergency",
      "status": "PENDING"
    }
  ]
}
```

## 3. Submit WFH Request (Employee)
- **Endpoint**: `POST /api/wfh/request`
- **Body**:
```json
{
  "from_date": "2026-06-15",
  "to_date": "2026-06-20",
  "reason": "Personal work at home"
}
```
- **Description**: Employees submit their own requests for approval.

## 4. WFH Management Action (Manager/HR/Admin)
- **Endpoint**: `PATCH /api/wfh/<int:id>/action`
- **Body**:
```json
{
  "status": "APPROVED", // or "REJECTED"
  "comments": "OK, approved for this week."
}
```
- **Description**: Approve or Reject an employee's WFH request.
