import qrcode
import os
import json
from flask import current_app

def generate_id_card_qr(card_id, employee_id, employee_code, company_name):
    """
    Generates a QR code for an ID card and returns the relative file path.
    """
    # Industry Standard: Store a verification payload or URL
    payload = {
        "card_id": card_id,
        "emp_id": employee_id,
        "emp_code": employee_code,
        "company": company_name
    }
    
    qr_data = json.dumps(payload)
    
    # Configure QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Ensure directory exists
    qr_dir = os.path.join('uploads', 'qrcodes')
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)
        
    # Save file
    filename = f"{card_id}.png"
    file_path = os.path.join(qr_dir, filename)
    img.save(file_path)
    
    # Return relative path for DB storage
    return f"uploads/qrcodes/{filename}"
