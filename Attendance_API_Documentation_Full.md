# Attendance Module API Documentation

This document maps the HRMS UI features to their backend API endpoints for the Attendance module.

## 1. Attendance Dashboard
**UI Feature**: Overview of today's attendance stats, shift distribution, and weekly trends.

| Feature | Endpoint | Method | Role Required |
| --- | --- | --- | --- |
| **Get Dashboard Stats** | `/api/attendance/dashboard-stats` | GET | Admin / HR / Manager |
| **Attendance List (Table)** | `/api/attendance` | GET | Admin / HR / Manager |
| *Filters*: `role`, `department`, `day` (today/all), `from_date`, `to_date`, `month`, `search`. | | | |

## 2. Manual Attendance Entry
**UI Feature**: "Manual Entry" button to add or edit a specific attendance record.

| Feature | Endpoint | Method | Role Required |
| --- | --- | --- | --- |
| **Create/Upsert Manual** | `/api/attendance/manual` | POST | Admin / HR / Manager |
| **Update Record** | `/api/attendance/<int:id>` | PUT | Admin / HR / Manager |
| **Delete Record** | `/api/attendance/<int:id>` | DELETE | Admin / HR / Manager |
| **Employee Details Lookup** | `/api/attendance/employee-details/<emp_id>` | GET | Admin / HR / Manager |

**Payload (Create/Manual)**:
```json
{
  "employee_id": "FIS0001",
  "date": "2023-10-25",
  "status": "Present",
  "login_at": "09:30",
  "logout_at": "18:30",
  "remarks": "Manual punch"
}
```

## 3. Bulk Attendance Entry
**UI Feature**: "Bulk Attendance" tab for marking attendance for multiple employees at once.

| Feature | Endpoint | Method | Role Required |
| --- | --- | --- | --- |
| **Get Employee Status List** | `/api/attendance/bulk-list?date=YYYY-MM-DD` | GET | Admin / HR / Manager |
| **Save Bulk Updates** | `/api/attendance/bulk-save` | POST | Admin / HR / Manager |
| **Import from CSV** | `/api/attendance/import` | POST | Admin / HR / Manager |

## 4. Shift & Policy Management
**UI Feature**: "Shift View" and "Configure Shifts".

| Feature | Endpoint | Method | Role Required |
| --- | --- | --- | --- |
| **List All Shifts** | `/api/shifts` | GET | Admin / HR / Manager |
| **Create New Shift** | `/api/shifts` | POST | Admin / HR |
| **Update Shift** | `/api/shifts/<int:id>` | PUT | Admin / HR |
| **Assign Shift to Emp** | `/api/shifts/assign` | POST | Admin / HR / Manager |
| **List Assignments** | `/api/shifts/assignments` | GET | Admin / HR / Manager |

## 5. Regularization (Attendance Correction)
**UI Feature**: "Regularization" tab for employees to request corrections and admins to approve.

| Feature | Endpoint | Method | Role Required |
| --- | --- | --- | --- |
| **Submit Request** | `/api/attendance/regularization/request` | POST | Employee |
| **My Requests** | `/api/attendance/regularization/my-requests` | GET | Employee |
| **Pending Requests** | `/api/attendance/regularization/pending` | GET | Admin / HR / Manager |
| **Approve Request** | `/api/attendance/regularization/<id>/approve` | POST | Admin / HR / Manager |
| **Reject Request** | `/api/attendance/regularization/<id>/reject` | POST | Admin / HR / Manager |

## 6. Device Management & Sync (AIPS)
**UI Feature**: "Devices" and "Sync Logs".

| Feature | Endpoint | Method | Role Required |
| --- | --- | --- | --- |
| **Device Heartbeat** | `/api/attendance/features/device/heartbeat` | POST | System (Device) |
| **Batch Sync Punches** | `/api/attendance/features/punch/batch-upload` | POST | System (Device) |
| **Sync Status/Logs** | `/api/attendance/features/punch/processed` | GET (TBD) | Admin / HR |

> [!NOTE]
> Device CRUD (Add/Edit Device) endpoints appear to be part of an unregistered module (`attendance_features_bp`). The UI interaction for these features may currently use mock data or the registration is pending.

## 7. ID Card Generation
**UI Feature**: "ID Card" tab for viewing and reissue requests.

| Feature | Endpoint | Method | Role Required |
| --- | --- | --- | --- |
| **List ID Cards** | `/api/id-card/list` | GET | Admin / HR |
| **Get Employee ID Card** | `/api/id-card/employee/<emp_id>` | GET | Employee / Admin |
| **Create ID Card** | `/api/id-card/create` | POST | Admin / HR |
| **Request Reissue** | `/api/id-card/reissue` | POST | Employee |
