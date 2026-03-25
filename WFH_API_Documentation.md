# WFH (Work From Home) Management API Documentation

This document describes the APIs for managing remote work and WFH requests.

## 1. WFH Dashboard Summary
**Endpoint**: `GET /api/wfh/summary`
**Description**: Returns overall counts for the WFH status tiles.

**Response Structure**:
```json
{
  "total": 12,
  "pending": 2,
  "approved": 8,
  "rejected": 2
}
```

## 2. WFH Request Log
**Endpoint**: `GET /api/wfh/requests`
**Description**: Returns a list of WFH requests. Supports filtering by status and search by employee/department.

**Query Parameters**:
- `status`: `All`, `Pending`, `Approved`, `Rejected` (Optional)
- `search`: Name or Department (Optional)

**Response Item Structure**:
```json
{
  "id": 1,
  "employee_name": "John Doe",
  "department": "Engineering",
  "period": "2025-06-01 - 2025-06-05",
  "from_date": "2025-06-01",
  "to_date": "2025-06-05",
  "days": 5,
  "reason": "Medical Emergency",
  "status": "PENDING",
  "created_at": "2025-05-25T10:00:00"
}
```

## 3. Allocate WFH (Create Request)
**Endpoint**: `POST /api/wfh/allocate`
**Description**: Create a new WFH allocation for an employee.

**Request Payload**:
```json
{
  "employee_id": "EMP001", 
  "from_date": "2025-06-01",
  "to_date": "2025-06-05",
  "reason": "Project Deadline"
}
```

## 4. Approval Actions
**Endpoints**:
- **Approve**: `POST /api/wfh/<id>/approve`
- **Reject**: `POST /api/wfh/<id>/reject`

**Description**: Updates the status of a specific WFH request.
