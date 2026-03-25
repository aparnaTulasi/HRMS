# HR Payroll Management API Access Documentation

This document outlines the API endpoints accessible to the **HR** role within the HRMS Payroll module. 

### Security & Filtering Rules:
*   **Role-Based Access**: Access is controlled via the `@require_roles` decorator.
*   **Subordinate Filtering**: When an HR user accesses employee-specific data (Payslips, Salary Register, Assignments, etc.), the system automatically filters the results to show **only** records belonging to users with the `MANAGER` or `EMPLOYEE` roles.
*   **Forbidden Access**: HR users are explicitly blocked from viewing or managing payroll data for `ADMIN` or `SUPER_ADMIN` users.

---

## 1. Pay Grade Management
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/superadmin/paygrades` | GET | SA, **HR** | List all active pay grades. |
| `/api/superadmin/paygrades/pdf` | GET | SA, **HR** | Download pay grades list as PDF. |
| `/api/account/paygrades` | GET | ACC, **HR** | List active pay grades for the company. |
| `/api/account/paygrades` | POST | ACC, **HR** | Create a new pay grade. |
| `/api/account/paygrades/<id>` | PUT | ACC, **HR** | Update an existing pay grade. |
| `/api/account/paygrades/<id>` | DELETE | ACC, **HR** | Delete a pay grade. |
| `/api/account/paygrades/pdf` | GET | ACC, **HR** | Download pay grades list as PDF. |

## 2. Pay Role Management
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/account/payroles` | GET | ACC, **HR** | List all active pay roles. |
| `/api/account/payroles` | POST | ACC, **HR** | Create a new pay role. |
| `/api/account/payroles/<id>` | PUT | ACC, **HR** | Update an existing pay role. |
| `/api/account/payroles/<id>` | DELETE | ACC, **HR** | Delete a pay role. |

## 3. Payslip Management
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/admin/payslips` | GET | ADMIN, **HR** | List payslips. (**HR: Manager/Employee only**) |
| `/api/admin/payslips/<id>` | GET | ADMIN, **HR** | View payslip details. (**HR: Manager/Employee only**) |
| `/api/admin/payslips/<id>/pdf` | GET | ADMIN, **HR** | Download PDF. (**HR: Manager/Employee only**) |
| `/api/account/payslips` | GET | ACC, **HR** | List payslips (Filtered for HR). |
| `/api/account/payslips` | POST | ACC, **HR** | Create a payslip. |
| `/api/account/payslips/<id>` | PUT | ACC, **HR** | Update a payslip. |
| `/api/account/payslips/<id>` | DELETE | ACC, **HR** | Delete a payslip. |

## 4. Payroll Change Requests
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/account/payroll/requests` | POST | ACC, **HR** | Create a change request. |
| `/api/superadmin/payroll/requests` | GET | SA, **HR** | List requests. (**HR: Manager/Employee only**) |
| `/api/admin/payroll/requests` | GET | ADMIN, **HR** | List requests. (**HR: Manager/Employee only**) |
| `/api/superadmin/payroll/requests/<id>/approve` | POST | SA, **HR** | Approve PayGrade/Role requests. |
| `/api/admin/payroll/requests/<id>/approve` | POST | ADMIN, **HR** | Approve PaySlip requests. |

## 5. Salary Structure & Components
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/superadmin/salary-assignments` | GET | SA, ADMIN, ACC, **HR** | List assignments. (**HR: Filtered**) |
| `/api/superadmin/payroll/components` | GET | SA, ADMIN, **HR** | List salary components. |
| `/api/superadmin/payroll/components` | POST | SA, ADMIN, **HR** | Create a component. |
| `/api/superadmin/payroll/components/<id>` | DELETE | SA, ADMIN, **HR** | Delete a component. |
| `/api/superadmin/payroll/structures` | GET | SA, ADMIN, **HR** | List salary structures. |
| `/api/superadmin/payroll/structures` | POST | SA, ADMIN, **HR** | Create a structure. |

## 6. Statutory & Dashboard
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/superadmin/payroll/statutory` | GET | SA, ADMIN, **HR** | View statutory settings. |
| `/api/superadmin/payroll/statutory` | PUT | SA, ADMIN, **HR** | Update statutory settings. |
| `/api/admin/payroll/dashboard` | GET | SA, ADMIN, **HR** | Payroll dashboard. (**HR: Filtered**) |
| `/api/payroll/reports/salary-register` | GET | SA, ADMIN, **HR** | Salary Register report. (**HR: Filtered**) |
| `/api/payroll/reports/income-tax` | GET | SA, ADMIN, **HR** | Income Tax Deductions report. (**HR: Filtered**) |
| `/api/payroll/reports/professional-tax` | GET | SA, ADMIN, **HR** | Professional Tax Deductions report. (**HR: Filtered**) |
| `/api/payroll/reports/general-ledger` | GET | SA, ADMIN, **HR** | General Ledger report. (**HR: Filtered**) |
| `/api/payroll/reports/accounts-payable` | GET | SA, ADMIN, **HR** | Accounts Payable report. (**HR: Filtered**) |

## 7. Compliance & Letters
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/payroll/form16` | GET | SA, ADMIN, **HR** | Manage Form-16 certificates. |
| `/api/payroll/form16` | POST | SA, ADMIN, **HR** | Update Form-16 data. |
| `/api/payroll/fnf` | GET | SA, ADMIN, **HR** | Manage F&F records. |
| `/api/payroll/fnf` | POST | SA, ADMIN, **HR** | Update F&F records. |
| `/api/payroll/letters` | GET | SA, ADMIN, **HR** | List payroll letters. |
| `/api/payroll/letters` | POST | SA, ADMIN, **HR** | Issue a payroll letter. |
| `/api/payroll/employees` | GET | SA, ADMIN, **HR** | HR Payroll Admin list. (**HR: Filtered**) |

## 8. Dropdown Helpers
| Endpoint | Method | Role | Description |
| --- | --- | --- | --- |
| `/api/superadmin/employees-dropdown` | GET | SA, ADMIN, ACC, **HR** | Dropdown for employees. |
| `/api/superadmin/paygrades-dropdown` | GET | SA, ADMIN, ACC, **HR** | Dropdown for pay grades. |
| `/api/superadmin/structures-dropdown` | GET | SA, ADMIN, ACC, **HR** | Dropdown for structures. |
| `/api/superadmin/components-dropdown` | GET | SA, ADMIN, ACC, **HR** | Dropdown for components. |
