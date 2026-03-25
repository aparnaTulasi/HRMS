# Payroll Management API Documentation

This document provides a detailed list of all APIs related to Payroll Management within the HRMS system. All endpoints are prefixed with `/api`.

## 1. Pay Grade Management
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/superadmin/paygrades` | GET | SUPER_ADMIN | List all active pay grades. |
| `/superadmin/paygrades/pdf` | GET | SUPER_ADMIN | Download pay grades list as PDF. |
| `/account/paygrades` | GET | ACCOUNT | List all active pay grades for the company. |
| `/account/paygrades` | POST | ACCOUNT | Create a new pay grade. |
| `/account/paygrades/<id>` | PUT | ACCOUNT | Update an existing pay grade. |
| `/account/paygrades/<id>` | DELETE | ACCOUNT | Delete a pay grade (Soft delete). |
| `/account/paygrades/pdf` | GET | ACCOUNT | Download pay grades list as PDF. |

## 2. Pay Role Management
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/account/payroles` | GET | ACCOUNT | List all active pay roles. |
| `/account/payroles` | POST | ACCOUNT | Create a new pay role. |
| `/account/payroles/<id>` | PUT | ACCOUNT | Update an existing pay role. |
| `/account/payroles/<id>` | DELETE | ACCOUNT | Delete a pay role. |

## 3. Payslip Management
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/admin/payslips` | GET | ADMIN, HR | List all payslips with filters. (HR: Manager/Employee only) |
| `/admin/payslips` | POST | ADMIN | Create a payslip manually. |
| `/admin/payslips/generate` | POST | ADMIN | Auto-generate a payslip based on structure and attendance. |
| `/admin/payslips/<id>` | GET | ADMIN, HR | Get detailed information for a specific payslip. (HR: Manager/Employee only) |
| `/admin/payslips/<id>` | PUT | ADMIN | Update an existing payslip. |
| `/admin/payslips/<id>` | DELETE | ADMIN | Delete a payslip. |
| `/admin/payslips/<id>/pdf` | GET | ADMIN, HR | Download payslip PDF. (HR: Manager/Employee only) |
| `/account/payslips` | GET | ACCOUNT | List payslips (Same as Admin). |
| `/account/payslips` | POST | ACCOUNT | Create a payslip (Same as Admin). |
| `/account/payslips/<id>` | PUT | ACCOUNT | Update a payslip (Same as Admin). |
| `/account/payslips/<id>` | DELETE | ACCOUNT | Delete a payslip (Same as Admin). |
| `/account/payslips/<id>/pdf` | GET | ACCOUNT | Download payslip PDF. |

## 4. Employee Self-Service (Payroll)
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/employee/payslips` | GET | EMPLOYEE | List current employee's payslips. |
| `/employee/payslips/<id>` | GET | EMPLOYEE | Get details of a specific personal payslip. |
| `/employee/payslips/<id>/pdf` | GET | EMPLOYEE | Download personal payslip PDF. |

## 5. Payroll Change Requests (Approval Workflow)
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/account/payroll/requests` | POST | ACCOUNT | Create a request for changes (PayGrade, PayRole, PaySlip). |
| `/superadmin/payroll/requests` | GET | SUPER_ADMIN | List payroll requests for Super Admin. |
| `/admin/payroll/requests` | GET | ADMIN | List payroll requests for Admin. |
| `/superadmin/payroll/requests/<id>/approve` | POST | SUPER_ADMIN | Approve PayGrade or PayRole requests. |
| `/admin/payroll/requests/<id>/approve` | POST | ADMIN | Approve PaySlip requests. |

## 6. Salary Structure & Components (Modular System)
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/superadmin/salary-assignments` | GET | SA, ADMIN, ACC, HR | List salary structure assignments. (HR: Manager/Employee only) |
| `/superadmin/salary-assignments` | POST | SA, ADMIN, ACC | Assign a salary structure to an employee. |
| `/superadmin/payroll/components` | GET | SA, ADMIN | List all available salary components. |
| `/superadmin/payroll/components` | POST | SA, ADMIN | Create a new salary component (Earning/Deduction). |
| `/superadmin/payroll/components/<id>` | DELETE | SA, ADMIN | Delete a salary component. |
| `/superadmin/payroll/structures` | GET | SA, ADMIN | List all salary structures. |
| `/superadmin/payroll/structures` | POST | SA, ADMIN | Create a salary structure (grouping components). |

## 7. Statutory & Dashboard
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/superadmin/payroll/statutory` | GET | SA, ADMIN | Get company statutory settings (PF, ESI, TDS). |
| `/superadmin/payroll/statutory` | PUT | SA, ADMIN | Update statutory settings. |
| `/admin/payroll/dashboard` | GET | SA, ADMIN | Get payroll analytics and summary stats. |
| `/payroll/reports/salary-register` | GET | SA, ADMIN, HR | Generate a salary register report. (HR: Manager/Employee only) |

## 8. Compliance & Letters
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/payroll/form16` | GET | ALL (By Token) | Fetch Form-16 tax certificates. |
| `/payroll/form16` | POST | ALL (By Token) | Save or update Form-16 data. |
| `/payroll/fnf` | GET | ALL (By Token) | Fetch Full & Final settlement records. |
| `/payroll/fnf` | POST | ALL (By Token) | Save or update F&F records. |
| `/payroll/letters` | GET | ALL (By Token) | List issued payroll letters. |
| `/payroll/letters` | POST | ALL (By Token) | Issue a new payroll letter. |
| `/payroll/employees` | GET | SA, ADMIN, HR | List employees for payroll administration. (HR: Manager/Employee only) |

## 9. Dropdown Helpers
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/superadmin/employees-dropdown` | GET | SA, ADMIN, ACC, HR | Get simplified employee list for dropdowns. |
| `/superadmin/paygrades-dropdown` | GET | SA, ADMIN, ACC, HR | Get active pay grades for dropdowns. |
| `/superadmin/structures-dropdown` | GET | SA, ADMIN, ACC, HR | Get salary structures for dropdowns. |
| `/superadmin/components-dropdown` | GET | SA, ADMIN, ACC, HR | Get salary components for dropdowns. |
