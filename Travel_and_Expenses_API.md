# Travel & Expenses API Documentation

**Base URL**: `/api/expenses`

## 1. Dashboard Statistics
- **Endpoint**: `GET /api/expenses/stats`
- **Description**: Returns stats cards data (Total Expenses YTD, Pending Claims, Approved Trips). Scoped to individual employee for standard users, and company-wide for Admin/HR.
- **Response**:
```json
{
  "success": true,
  "data": {
    "total_expenses_ytd": 450.0,
    "pending_claims": 2,
    "approved_trips": 1,
    "currency": "$"
  }
}
```

## 2. Expense Trends (Chart)
- **Endpoint**: `GET /api/expenses/trends`
- **Description**: Returns the last 6 months of approved expense sums for the trend graph.
- **Response**:
```json
{
  "success": true,
  "data": [
    {"month": "Jan", "amount": 1200},
    {"month": "Feb", "amount": 850},
    ...
  ]
}
```

## 3. Expense Claims List
- **Endpoint**: `GET /api/expenses/claims`
- **Description**: Returns a list of expense claims. Employees see only their own, while Admin/HR see all.
- **Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "employee_name": "Tulasi",
      "project_purpose": "Client Meeting NYC",
      "category": "Flight",
      "amount": 250.0,
      "expense_date": "2026-04-07",
      "status": "APPROVED",
      "description": "Travel for project work"
    }
  ]
}
```

## 4. Submit New Claim
- **Endpoint**: `POST /api/expenses/claims`
- **Body**:
```json
{
  "project_purpose": "Client Meeting NYC",
  "category": "Flight",
  "amount": 250.0,
  "currency": "$",
  "expense_date": "07-04-2026",
  "description": "Round trip ticket to NYC"
}
```
- **Description**: Submits a new claim. The backend automatically records the **Day/Time/Year/Month** and the Name of the submitter for audit tracking.

## 5. Expense Action (Approve/Reject)
- **Endpoint**: `PATCH /api/expenses/claims/<int:id>/action`
- **Body**:
```json
{
  "action": "APPROVE"  // or "REJECT"
}
```
- **Description**: Higher authority level action to approve or reject a claim.

## 6. Budget Utilization (Admin only)
- **Endpoint**: `GET /api/expenses/budget-utilization`
- **Description**: Returns data for the target/utilization progress bars.
- **Response**:
```json
{
  "success": true,
  "data": [
    {"department": "Marketing Dept", "utilization": 80},
    {"department": "Sales Operations", "utilization": 42}
  ]
}
```
