import os
import uuid
from flask import Blueprint, request, jsonify, g, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models import db
from utils.decorators import token_required

user_bp = Blueprint('user', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_bp.route('/profile-pic', methods=['POST'])
@token_required
def upload_profile_pic():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        # Generate unique filename: user_ID_UUID.ext
        new_filename = f"user_{g.user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
        
        # Define upload path
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile_pics')
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, new_filename)
        file.save(file_path)
        
        # Save URL to database
        g.user.profile_pic = f"/api/user/profile-pic/{new_filename}"
        db.session.commit()
        
        return jsonify({'message': 'Profile picture uploaded', 'url': g.user.profile_pic}), 200
    
    return jsonify({'message': 'Invalid file type. Allowed: png, jpg, jpeg, gif'}), 400

@user_bp.route('/profile-pic/<filename>', methods=['GET'])
def get_profile_pic(filename):
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile_pics')
    return send_from_directory(upload_folder, filename)