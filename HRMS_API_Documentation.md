# HRMS API Documentation

This document provides details for the Authentication and Attendance APIs of the Human Resource Management System (HRMS).

---

## 1. Authentication APIs (Login & Signup)

### [POST] /super-admin/signup
*   **Description**: Registers a new Super Admin account.
*   **Payload**:
    ```json
    {
      "email": "admin@example.com",
      "password": "securepassword",
      "first_name": "John",
      "last_name": "Doe"
    }
    ```
*   **Response (201)**: `{"message": "Signup successful. OTP sent to email."}`

### [POST] /verify-signup-otp
*   **Description**: Verifies the OTP sent during signup to activate the account.
*   **Payload**: `{"otp": "123456"}`
*   **Response (200)**: `{"message": "OTP verified. Super Admin account activated.", "status": "ACTIVE"}`

### [POST] /login
*   **Description**: Authenticates a user and returns a JWT token.
*   **Payload**:
    ```json
    {
      "email": "user@example.com",
      "password": "yourpassword"
    }
    ```
*   **Response (200)**:
    ```json
    {
      "token": "JWT_TOKEN_HERE",
      "user": {
        "id": 1,
        "email": "user@example.com",
        "role": "ADMIN",
        "name": "John Doe",
        "company_id": 5
      },
      "redirect_url": "https://company.hrms.com/admin/dashboard"
    }
    ```

### [POST] /forgot-password
*   **Description**: Sends a password reset OTP to the user's email.
*   **Payload**: `{"email": "user@example.com"}`

### [POST] /reset-password
*   **Description**: Resets the password using a reset token or OTP.
*   **Payload**:
    ```json
    {
      "reset_token": "TOKEN",
      "new_password": "newsecurepassword",
      "confirm_password": "newsecurepassword"
    }
    ```

---

## 2. Attendance APIs (Role-Based)

### Role-Based Access Control
*   **SUPER_ADMIN**: Full access to all attendance records across all companies.
*   **ADMIN / HR / MANAGER**: Can manage (create, edit, delete, import) attendance for employees within their own company.
*   **EMPLOYEE**: Can only view their own attendance records.

### [GET] /api/attendance
*   **Description**: Lists attendance records with filters.
*   **Role**: ADMIN, HR, MANAGER, SUPER_ADMIN
*   **Query Parameters**: `role`, `department`, `day` (today/all), `from_date`, `to_date`, `search`.
*   **Response**: List of attendance objects.

### [POST] /api/attendance/manual
*   **Description**: Manually marks attendance for an employee.
*   **Role**: ADMIN, HR, MANAGER, SUPER_ADMIN (Cannot mark own attendance)
*   **Payload**:
    ```json
    {
      "employee_id": "EMP001",
      "date": "2025-03-25",
      "status": "Present",
      "login_at": "09:00 AM",
      "logout_at": "06:00 PM",
      "remarks": "Manual Entry"
    }
    ```

### [POST] /api/attendance/bulk-save
*   **Description**: Saves attendance for multiple employees at once.
*   **Role**: ADMIN, HR, MANAGER, SUPER_ADMIN
*   **Payload**:
    ```json
    {
      "date": "2025-03-25",
      "updates": [
        { "employee_id": 1, "status": "Present", "shift_id": 1 },
        { "employee_id": 2, "status": "Absent" }
      ]
    }
    ```

### [GET] /api/attendance/me
*   **Description**: Retrieves the logged-in user's own attendance history.
*   **Role**: All Authenticated Users.

### [POST] /api/attendance/regularization/request
*   **Description**: Submits a request to correct attendance data.
*   **Role**: EMPLOYEE
*   **Payload**:
    ```json
    {
      "attendance_date": "2025-03-20",
      "requested_status": "Present",
      "requested_login_at": "09:30 AM",
      "reason": "Forgot to punch in"
    }
    ```

### [GET] /api/attendance/dashboard-stats
*   **Description**: Returns real-time attendance statistics (Present, Absent, Trends).
*   **Role**: ADMIN, HR, MANAGER, SUPER_ADMIN

---
