# Support Helpdesk API Documentation

**Base URL**: `/api/support`

## 1. Helpdesk Configuration (Drop-downs)
- **Endpoint**: `GET /api/support/config`
- **Description**: Returns the valid options for **Category** and **Priority** to populate frontend drop-downs.
- **Response**:
```json
{
  "success": true,
  "data": {
    "categories": ["IT Support", "Payroll", "HR Query", "Office Admin", "Others"],
    "priorities": ["Low", "Medium", "High", "Urgent"]
  }
}
```

## 2. Dashboard Statistics
- **Endpoint**: `GET /api/support/dashboard-stats`
- **Description**: Returns counts for Total, Open, In Progress, and Resolved tickets. Employees see their own stats; Admins see company-wide stats.
- **Response**:
```json
{
  "success": true,
  "data": {
    "total_tickets": 10,
    "open": 2,
    "in_progress": 3,
    "resolved": 5
  }
}
```

## 3. Tickets List
- **Endpoint**: `GET /api/support/tickets`
- **Description**: Returns a list of support tickets.
- **Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": "SUP-001",
      "subject": "Email not working",
      "category": "IT Support",
      "priority": "High",
      "status": "In Progress",
      "date": "2026-04-07"
    }
  ]
}
```

## 4. Raise New Ticket
- **Endpoint**: `POST /api/support/tickets`
- **Body**:
```json
{
  "subject": "Payroll discrepancy for March",
  "category": "Payroll",
  "priority": "Medium",
  "description": "My bonus was not included in the last payslip.",
  "attachment_url": null
}
```
- **Description**: Creates a new ticket with a sequential ID (e.g., SUP-001).

## 5. Ticket Action (Status Update)
- **Endpoint**: `PATCH /api/support/tickets/<int:id>/action`
- **Body**:
```json
{
  "status": "Resolved", // or "In Progress"
  "priority": "High"
}
```
- **Description**: Management role action to update ticket status or priority.
