# HRMS Concise API List

## 1. Authentication (Logins & Signups)
- `POST /api/auth/super-admin/signup` : Super Admin registration
- `POST /api/auth/verify-signup-otp` : Signup OTP verification
- `POST /api/auth/login` : User authentication
- `POST /api/auth/forgot-password` : Request reset OTP
- `POST /api/auth/verify-reset-otp` : Verify reset OTP & get token
- `POST /api/auth/reset-password` : Reset password
- `POST /api/auth/change-password` : Update password
- `GET /api/auth/me` : Current user session info

## 2. Attendance
- `GET /api/attendance` : List attendance with filters
- `POST /api/attendance/manual` : Create/Update attendance manually
- `GET /api/attendance/me` : View personal attendance history
- `POST /api/attendance/login` : Mark daily punch-in
- `POST /api/attendance/logout` : Mark daily punch-out
- `POST /api/attendance/bulk-save` : Manage multiple employees at once
- `GET /api/attendance/dashboard-stats` : Attendance overview (Counts, Trends)
- `POST /api/attendance/regularization/request` : Request attendance corrections
- `GET /api/attendance/regularization/pending` : Pending approval requests
- `POST /api/attendance/regularization/<int:request_id>/approve` : Approve correction
- `POST /api/attendance/regularization/<int:request_id>/reject` : Reject correction
