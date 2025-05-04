# -*- coding: utf-8 -*-
import os
import uuid
import datetime
import json
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    jsonify, send_from_directory, flash, abort, current_app
)
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError

# Relative imports for models and extensions
from ..models.user import User, UserRole
from ..models.report import Report, ReportStatus, ReportImportance
from ..extensions import db

main_bp = Blueprint("main", __name__)

# --- Report Categories and Importance ---
REPORT_CATEGORIES = {
    "حادث مروري": ReportImportance.HIGH,
    "حريق": ReportImportance.HIGH,
    "مشاجرة": ReportImportance.HIGH,
    "فيضان": ReportImportance.HIGH,
    "تحرش": ReportImportance.HIGH,
    "حالة طبية": ReportImportance.HIGH,
    "اعتداء على رجل امن": ReportImportance.HIGH,
    "شعارات سياسية": ReportImportance.HIGH,
    "امطار غزيرة": ReportImportance.MEDIUM,
    "عاصفة رملية": ReportImportance.MEDIUM,
    "اعتداء لفظي": ReportImportance.MEDIUM,
    "انقطاع التيار الكهربائي": ReportImportance.MEDIUM,
    "حالة تقنية": ReportImportance.MEDIUM,
    "تعطل اشارة مرور": ReportImportance.LOW,
    "تعطل مركبة": ReportImportance.LOW,
    "صيانة": ReportImportance.LOW,
    "اخرى": ReportImportance.LOW
}

# --- Location List ---
LOCATIONS = [
    "بوابة سمحان", "مواقف سمحان", "فندق سمحان", "السمحانية", "البجيري", 
    "الزلال", "الثقافة", "الطريف", "طريق الملك عبدالعزيز", "طريق الملك فهد", 
    "طريق الملك فيصل", "طريق المديد", "طريق وادي حنيفة", "بوابة صفار", 
    "وادي صفار", "المباني الادارية", "هيئة تطوير بوابة الدرعية", 
    "ساحة البلدية", "طريق الامام", "طريق الامير سطام", "اخرى"
]

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# --- Routes ---
@main_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('main.login')) # Use blueprint name
    return redirect(url_for('main.inbox')) # Use blueprint name

@main_bp.route('/inbox')
@login_required
def inbox():
    # Fetch reports assigned or escalated to the current user
    assigned_reports = Report.query.filter_by(assigned_to_id=current_user.id, status=ReportStatus.ASSIGNED).order_by(Report.submission_time.desc()).all()
    escalated_reports = Report.query.filter_by(escalated_to_id=current_user.id, status=ReportStatus.ESCALATED).order_by(Report.submission_time.desc()).all()
    return render_template('inbox.html', assigned_reports=assigned_reports, escalated_reports=escalated_reports)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'danger')
            return redirect(url_for('main.login'))
        login_user(user, remember=remember)
        flash('تم تسجيل الدخول بنجاح.', 'success')
        next_page = request.args.get('next')
        # Add basic security check for next_page if needed (e.g., using urllib.parse.urlparse and url_join)
        return redirect(next_page or url_for('main.index'))
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج.', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/report')
# @login_required # Decide if report submission requires login
def report_page():
    report_category_list = list(REPORT_CATEGORIES.keys())
    report_categories_importance = {k: v.value for k, v in REPORT_CATEGORIES.items()}
    return render_template('report.html', report_categories=report_category_list, locations=LOCATIONS, report_categories_importance=report_categories_importance)

@main_bp.route('/track')
@login_required
def track_page():
    query = Report.query
    # Non-managers see only reports they are involved in?
    if current_user.role not in [UserRole.SECURITY_MANAGER, UserRole.PROJECT_MANAGER, UserRole.REPORTS_SPECIALIST]:
         query = query.filter(
             (Report.assigned_to_id == current_user.id) | 
             (Report.escalated_to_id == current_user.id)
             # Add submitted_by_id if implemented and needed
         )
         
    reports = query.order_by(Report.submission_time.desc()).all()
    
    # Get users for assignment dropdown
    users_for_assignment = User.query.filter(User.role.in_([UserRole.OPERATOR, UserRole.SUPERVISOR])).all() 
    all_statuses = [s.value for s in ReportStatus] # Get all status values for dropdown
    
    return render_template('track.html', reports=reports, users_for_assignment=users_for_assignment, all_statuses=all_statuses)

@main_bp.route('/submit_report', methods=['POST'])
# @login_required # Add if needed
def submit_report():
    try:
        report_id = str(uuid.uuid4())
        report_type = request.form.get('report_type')
        location_selected = request.form.get('location')
        location_other_details = request.form.get('location_other', '')
        
        if location_selected not in LOCATIONS:
             flash('الموقع المحدد غير صالح.', 'warning')
             report_category_list = list(REPORT_CATEGORIES.keys())
             report_categories_importance = {k: v.value for k, v in REPORT_CATEGORIES.items()}
             return render_template('report.html', report_categories=report_category_list, locations=LOCATIONS, report_categories_importance=report_categories_importance), 400
             
        location_final = location_selected
        if location_selected == 'اخرى':
            if not location_other_details:
                 flash('يرجى تحديد الموقع في خانة "أخرى".', 'warning')
                 report_category_list = list(REPORT_CATEGORIES.keys())
                 report_categories_importance = {k: v.value for k, v in REPORT_CATEGORIES.items()}
                 return render_template('report.html', report_categories=report_category_list, locations=LOCATIONS, report_categories_importance=report_categories_importance), 400
            # location_final remains 'اخرى', details stored separately

        importance_enum = REPORT_CATEGORIES.get(report_type, ReportImportance.LOW)

        new_report = Report(
            id=report_id,
            reporter_name=request.form.get('reporter_name'),
            reporter_id=request.form.get('reporter_id'),
            report_date=datetime.datetime.strptime(request.form.get('report_date'), '%Y-%m-%d').date() if request.form.get('report_date') else None,
            location=location_final,
            location_other=location_other_details if location_selected == 'اخرى' else None,
            report_type=report_type,
            importance=importance_enum,
            details=request.form.get('details'),
            action_taken=request.form.get('action_taken', ''),
            status=ReportStatus.RECEIVED
        )

        files = request.files.getlist('images')
        saved_filenames = []
        saved_files_count = 0
        for file in files:
            if file and allowed_file(file.filename):
                if saved_files_count >= current_app.config['MAX_IMAGES']:
                    flash(f'تم الوصول للحد الأقصى لعدد الصور ({current_app.config["MAX_IMAGES"]}). لم يتم حفظ الملفات الإضافية.', 'warning')
                    break
                
                filename_base = secure_filename(file.filename)
                unique_filename = f"{report_id}_{uuid.uuid4().hex[:8]}_{filename_base}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                
                try:
                    file.save(file_path)
                    saved_filenames.append(unique_filename)
                    saved_files_count += 1
                except Exception as save_error:
                    current_app.logger.error(f"Error saving file {filename_base}: {save_error}")
                    flash(f'حدث خطأ أثناء حفظ الملف {filename_base}.', 'error')
            elif file and file.filename != '':
                 flash(f'نوع الملف غير مسموح به: {file.filename}', 'warning')

        new_report.set_images(saved_filenames)

        db.session.add(new_report)
        db.session.commit()

        flash(f'تم استلام بلاغك بنجاح. رقم البلاغ: {report_id}', 'success')
        if current_user.is_authenticated:
             return redirect(url_for('main.track_page'))
        else:
             # Maybe show a simple confirmation page for anonymous users
             return render_template('submission_confirmation.html', report_id=report_id)

    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Database Integrity Error: {e}")
        flash('حدث خطأ في قاعدة البيانات أثناء حفظ البلاغ.', 'danger')
        report_category_list = list(REPORT_CATEGORIES.keys())
        report_categories_importance = {k: v.value for k, v in REPORT_CATEGORIES.items()}
        return render_template('report.html', report_categories=report_category_list, locations=LOCATIONS, report_categories_importance=report_categories_importance), 500
    except ValueError as e:
        current_app.logger.warning(f"Value Error (likely date format): {e}")
        flash('صيغة التاريخ غير صحيحة. يرجى استخدام YYYY-MM-DD.', 'warning')
        report_category_list = list(REPORT_CATEGORIES.keys())
        report_categories_importance = {k: v.value for k, v in REPORT_CATEGORIES.items()}
        return render_template('report.html', report_categories=report_category_list, locations=LOCATIONS, report_categories_importance=report_categories_importance), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in submit_report: {e}") 
        flash(f'حدث خطأ عام أثناء تقديم البلاغ. يرجى المحاولة مرة أخرى.', 'error')
        report_category_list = list(REPORT_CATEGORIES.keys())
        report_categories_importance = {k: v.value for k, v in REPORT_CATEGORIES.items()}
        return render_template('report.html', report_categories=report_category_list, locations=LOCATIONS, report_categories_importance=report_categories_importance), 500

@main_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    # Add security check if needed (e.g., check if user is allowed to see this file)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main_bp.route('/manage_users')
@login_required
def manage_users_page():
    # Authorization: Only allow certain roles (e.g., Project Manager)
    if current_user.role != UserRole.PROJECT_MANAGER:
        abort(403)
    users = User.query.all()
    roles = [r.value for r in UserRole] # Pass roles for the add/edit form
    return render_template('manage_users.html', users=users, roles=roles)

