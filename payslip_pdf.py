import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_payslip_pdf(payslip, out_dir="uploads/payslips"):
    os.makedirs(out_dir, exist_ok=True)
    filename = f"payslip_{payslip.company_id}_{payslip.employee_id}_{payslip.pay_month:02d}_{payslip.pay_year}.pdf"
    filepath = os.path.join(out_dir, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"SALARY SLIP - {payslip.pay_month:02d}/{payslip.pay_year}")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Employee ID (DB): {payslip.employee_id}")
    y -= 15
    c.drawString(50, y, f"Total Days: {payslip.total_days} | Paid: {payslip.paid_days} | LWP: {payslip.lwp_days}")
    y -= 20

    def draw_items(title, items):
        nonlocal y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, title)
        y -= 16

        c.setFont("Helvetica", 10)
        for it in items:
            c.drawString(60, y, it.component)
            c.drawRightString(width - 60, y, f"{float(it.amount):.2f}")
            y -= 13
            if y < 80:
                c.showPage()
                y = height - 50

        y -= 8

    draw_items("EARNINGS", payslip.earnings)
    draw_items("DEDUCTIONS", payslip.deductions)
    draw_items("EMPLOYER CONTRIBUTION", payslip.employer_contribs)
    draw_items("REIMBURSEMENTS", payslip.reimbursements)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, f"Gross Salary: {float(payslip.gross_salary):.2f}")
    y -= 14
    c.drawString(50, y, f"Total Deductions: {float(payslip.total_deductions):.2f}")
    y -= 14
    c.drawString(50, y, f"Total Reimbursement: {float(payslip.total_reimbursements):.2f}")
    y -= 14
    c.drawString(50, y, f"Net Salary: {float(payslip.net_salary):.2f}")

    c.showPage()
    c.save()
    return filepath