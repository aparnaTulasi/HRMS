# HRMS Back-End Project Documentation

## 1. Project Overview
The **Human Resource Management System (HRMS)** is a comprehensive, enterprise-level platform designed to automate and streamline core HR operations. This system serves as a centralized hub for managing the entire employee lifecycle—from recruitment and onboarding to payroll, performance tracking, and offboarding.

### Core Objectives
*   **Automation**: Automate manual HR processes like attendance tracking, payroll calculation, and tax deductions.
*   **Self-Service**: Provide a robust portal for employees to manage Leaves, WFH, and Desk Bookings.
*   **Security & Compliance**: Ensure data security with Role-Based Access Control (RBAC) and maintain a clear audit trail.
*   **Centralization**: Centralize document management, policy distribution, and organizational communication.

---

## 2. Technical Architecture
The platform is built with a **Micro-services inspired monolithic architecture** using Flask Blueprints. This ensures high scalability, maintenance ease, and modular development.

### Core Technology Stack
*   **Language**: Python 3.8+
*   **Framework**: Flask (Modular Blueprints)
*   **Database**: MySQL 8.0+ (Relational with InnoDB)
*   **ORM**: Flask-SQLAlchemy
*   **Authentication**: JWT (JSON Web Tokens) via Flask-JWT-Extended
*   **Migrations**: Alembic / Flask-Migrate

---

## 3. Project Structure
To navigate the codebase effectively, refer to the following directory structure:

```text
HRMS-main/
├── app.py                  # Main entry point & Blueprint registration
├── config.py               # Environment & App configurations
├── models/                 # Database Schemas (60+ models)
│   ├── user.py             # Auth & Role logic
│   ├── employee.py         # Core profile data
│   ├── payroll.py          # Extensive salary logic
│   └── ...                 # Feature-specific models
├── routes/                 # API Endpoints (Modularized by feature)
│   ├── auth.py             # Login, Signup, OTP logic
│   ├── attendance.py       # Attendance & Geo-fencing
│   └── ...                 # 40+ Feature blueprints
├── utils/                  # Shared utility functions
│   ├── decorators.py       # RBAC & Security decorators
│   ├── email_utils.py      # Automated notification logic
│   └── audit_logger.py     # System logging utilities
├── migrations/             # Database version control files
├── static/ & uploads/      # Document & Image storage
└── requirements.txt        # Dependency manifest
```

---

## 4. Setup & Installation Guide

### Step 1: Core Environment
1.  **Python**: Install Python 3.8+ and ensure it's added to your PATH.
2.  **MySQL**: Install MySQL Community Server and set a root password.

### Step 2: Database Initialization
Create an empty database named `hrms_db`:
```sql
CREATE DATABASE hrms_db;
```

### Step 3: Local Environment Setup
1.  Navigate to the project directory and create a virtual environment:
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    source venv/bin/activate  # Mac/Linux
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Step 4: Configuration (.env)
Create a `.env` file in the root folder with the following details:
```env
# Database Configuration
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=hrms_db
DB_HOST=localhost
DB_PORT=3306

# Security
SECRET_KEY=generate-a-long-random-string
JWT_SECRET_KEY=another-random-string

# App Settings
FLASK_APP=app.py
FLASK_ENV=development
```

### Step 5: Migration & Launch
1.  Apply database schema:
    ```bash
    flask db upgrade
    ```
2.  Start the development server:
    ```bash
    python app.py
    ```
    The API will be available at: `http://127.0.0.1:5000`

---

## 5. Security & Access Control (RBAC)
The system implements a multi-tier role hierarchy to protect sensitive data.

### Roles & Permissions
*   **Super Admin**: Global access, manage all companies, subscriptions, and system-wide settings.
*   **Admin**: Organization-level control, manage departments, branches, and HR managers.
*   **HR Manager**: Full access to the Employee Lifecycle, Payroll, and Document Verification.
*   **Manager**: Team-level management, approval of leaves, WFH, and visitor requests for subordinates.
*   **Employee**: Personal portal for attendance, salary slips, and support tickets.

### Security Implementation
We use custom decorators in `utils/decorators.py` to enforce security:
*   `@token_required`: Ensures the user is logged in via JWT.
*   `@role_required(['ADMIN', 'HR_MANAGER'])`: Restricts access to specific roles.
*   `@permission_required('VIEW_PAYROLL')`: Provides granular control over specific features.

---

## 6. Functional Modules Breakdown

### A. Identity & Access Management (IAM)
*   **Auth Module**: Secure signup/login with OTP verification.
*   **Audit Engine**: Every action is logged (User, IP, Action, Timestamp) for compliance.

### B. Life-cycle Management
*   **Recruitment**: Applicant tracking and interview pipeline.
*   **Onboarding**: Automated checklist from document collection to IT asset assignment.
*   **Exit Management**: Resignation workflow, clearance, and Final Settlement (FnF).

### C. Time & Operations
*   **Attendance**: Geo-fencing & IP restriction. Supports bulk imports and late mark logic.
*   **Leaves/WFH**: Fully automated approval workflows with real-time notifications.
*   **Desk Booking**: Modern office space management for hybrid work roles.

### D. Financials
*   **Payroll Engine**: Calculates TDS, Bonuses, LOP, and generates PDF Payslips.
*   **Loans & Expenses**: Employee loan tracking (EMI) and travel expense reimbursement flows.

### E. Resources
*   **Document Center**: Secure BLOB storage for sensitive ID proofs (Aadhar, PAN) with E-Sign support.
*   **Asset Tracking**: Manage inventory from laptops to physical office equipment.

---

## 7. Developer Utilities
The project includes several utility scripts for maintenance:
*   `seed_*.py`: Use these to populate the database with test data for development.
*   `cleanup_*.py`: Use these to reset specific modules or clear the database.
*   `backend_error.log`: Centralized file for tracking system errors.

---

## 8. Hardware Requirements
*   **RAM**: 4GB Minimum (8GB Recommended).
*   **Processor**: Intel i3 or equivalent (i5 Recommended).
*   **Storage**: 500MB initial (Grows with document uploads).

---

> [!TIP]
> **API Documentation**: For detailed endpoint level documentation, refer to the specific files like `HRMS_API_Documentation.md` and `Attendance_API_Documentation_Full.md` located in the root directory.
