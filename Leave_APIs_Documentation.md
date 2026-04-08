# My Leaves & Time Off - API Documentation

## 📅 Leave Calculation & Application
### 1. Calculate Leave Days
- **URL**: `POST /api/leaves/calculate-days`
- **Desc**: Calculates working days between two dates, excluding company holidays and weekends.
- **Payload**:
  ```json
  {
    "from_date": "2026-04-01",
    "to_date": "2026-04-01",
    "is_half_day": true,
    "leave_type_id": 1
  }
  ```
- **Response**: `{"total_units": 0.5}`

### 2. Apply for Leave
- **URL**: `POST /api/leaves/apply`
- **Desc**: Submits a leave request. Supports half-day and attachments.
- **Payload**:
  ```json
  {
    "leave_type_id": 1,
    "from_date": "2026-04-01",
    "to_date": "2026-04-01",
    "reason": "Doctor appointment",
    "is_half_day": true,
    "attachment_url": "https://...",
    "company_id": 1 (Optional for emp)
  }
  ```

---

## 📊 Dashboard (Employee View)
### 3. Dashboard Summary
- **URL**: `GET /api/leaves/my-dashboard/summary`
- **Desc**: Overall counts (Pending, Approved, Rejected) and Balance Distribution (Sick, Casual, etc.).
- **Response**:
  ```json
  {
    "counts": {"total_balance": 15.0, "pending": 2, "approved": 5, "rejected": 1},
    "distribution": [{"name": "Sick", "code": "SL", "value": 5.0}, ...]
  }
  ```

### 4. Leave Trends
- **URL**: `GET /api/leaves/my-dashboard/trends`
- **Desc**: Monthly count of approved leaves for the current year.
- **Response**: `[{"month": "Jan", "leaves": 2}, ...]`

### 5. Recent Requests
- **URL**: `GET /api/leaves/my-dashboard/recent`
- **Desc**: 5 most recent requests with status.
- **Response**: `[{"id": 1, "type": "Sick Leave", "period": "Apr 01 - Apr 01", "days": "0.5d", "status": "Pending"}]`

---

## 🕒 History & Balances
### 6. My History & Current Balances
- **URL**: `GET /api/leaves/mine`
- **Desc**: Combined view of all past leave requests and current balances. Supports `search`, `status`, `from`, `to`, and `leave_type_id` filters.
- **Response**:
  ```json
  {
    "leaves": [{"id": 1, "status": "Approved", "leave_type_name": "Sick Leave", "applied_on": "Mar 28, 2026", ...}, ...],
    "balances": [{"leave_type_name": "Sick Leave", "balance": 10.0}, ...]
  }
  ```

### 7. Standalone Balance
- **URL**: `GET /api/leaves/balance`
- **Desc**: Current balances only.
- **Response**: `[{"leave_type_name": "Sick Leave", "balance": 10.0}, ...]`
