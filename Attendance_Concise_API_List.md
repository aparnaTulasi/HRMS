# HRMS Attendance APIs - Concise List

## 1. Dashboard & Records
- `GET /api/attendance/dashboard-stats` - Get summary counts & trends.
- `GET /api/attendance` - List all records (supports filters: role, dept, date).
- `GET /api/attendance/me` - View own attendance (Employee).

## 2. Punctuality (Mark-In/Out)
- `POST /api/attendance/login` - Punch In.
- `POST /api/attendance/logout` - Punch Out.

## 3. Manual & Bulk Management
- `POST /api/attendance/manual` - Add/Edit manual attendance.
- `GET /api/attendance/bulk-list` - Fetch all employees for a date.
- `POST /api/attendance/bulk-save` - Save bulk status updates.
- `POST /api/attendance/import` - Bulk upload via CSV.

## 4. Shifts
- `GET /api/shifts` - View shift definitions.
- `POST /api/shifts/assign` - Link employee to a shift.
- `GET /api/shifts/assignments` - View who is on which shift.

## 5. Regularization (Corrections)
- `POST /api/attendance/regularization/request` - Submit correction.
- `GET /api/attendance/regularization/pending` - Review requests (Admin).
- `POST /api/attendance/regularization/<id>/approve` - Approve/Update record.

## 6. Devices & Sync (AIPS)
- `POST /api/attendance/features/device/heartbeat` - Device health check.
- `POST /api/attendance/features/punch/batch-upload` - Sync offline logs.

## 7. ID Cards
- `GET /api/id-card/list` - List all cards.
- `GET /api/id-card/employee/<id>` - View specific card.
- `POST /api/id-card/reissue` - Request replacement.
