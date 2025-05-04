# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request, abort, flash, redirect, url_for
from flask_login import login_required, current_user
from ..models.user import User, UserRole # Relative import
from ..models.report import Report, ReportStatus # Relative import
from ..extensions import db # Relative import
import datetime

report_actions_bp = Blueprint("report_actions", __name__, url_prefix="/reports")

# Define the escalation hierarchy
ESCALATION_ORDER = [
    UserRole.OPERATOR,
    UserRole.SUPERVISOR,
    UserRole.QUALITY,
    UserRole.SECURITY_MANAGER,
    UserRole.PROJECT_MANAGER
]

def get_next_escalation_role(current_role):
    try:
        current_index = ESCALATION_ORDER.index(current_role)
        if current_index < len(ESCALATION_ORDER) - 1:
            return ESCALATION_ORDER[current_index + 1]
        else:
            return None # Already at the top (Project Manager)
    except ValueError:
        return None # Role not in escalation path

def find_user_with_role(role):
    # Find *any* user with the target role. 
    # In a real system, you might need more complex logic 
    # (e.g., specific team, availability, round-robin).
    # For now, just find the first one.
    return User.query.filter_by(role=role).first()

@report_actions_bp.route("/<string:report_id>/assign", methods=["POST"])
@login_required
def assign_report(report_id):
    report = Report.query.get_or_404(report_id)
    assign_to_user_id = request.form.get("assign_to_user_id")

    # Authorization: Only supervisors or managers can assign?
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.SECURITY_MANAGER, UserRole.PROJECT_MANAGER]:
        flash("ليس لديك الصلاحية لإسناد البلاغات.", "danger")
        return redirect(url_for("track_page")) # Or report detail page

    assignee = User.query.get(assign_to_user_id)
    if not assignee:
        flash("المستخدم المحدد للإسناد غير موجود.", "warning")
        return redirect(url_for("track_page"))

    # Logic to check if the assignee role is appropriate (e.g., assign to Operator or Supervisor initially)
    # if assignee.role not in [UserRole.OPERATOR, UserRole.SUPERVISOR]:
    #     flash("لا يمكن إسناد البلاغ لهذا الدور مباشرة.", "warning")
    #     return redirect(url_for("track_page"))

    report.assigned_to_id = assignee.id
    report.escalated_to_id = None # Clear escalation if explicitly assigning
    report.status = ReportStatus.ASSIGNED
    report.add_escalation_step(current_user.id, assignee.id) # Log assignment as a step

    db.session.commit()
    flash(f"تم إسناد البلاغ بنجاح إلى {assignee.username}.")
    return redirect(url_for("track_page"))

@report_actions_bp.route("/<string:report_id>/escalate", methods=["POST"])
@login_required
def escalate_report(report_id):
    report = Report.query.get_or_404(report_id)

    # Authorization: Check if the current user can escalate this report
    # User must be the assignee or the one it's escalated to, or a manager?
    can_escalate = False
    if report.assigned_to_id == current_user.id:
        can_escalate = True
    elif report.escalated_to_id == current_user.id:
         can_escalate = True
    # Allow managers to escalate any report? (Optional)
    # elif current_user.role in [UserRole.SECURITY_MANAGER, UserRole.PROJECT_MANAGER]:
    #    can_escalate = True 

    if not can_escalate:
        flash("ليس لديك الصلاحية لتصعيد هذا البلاغ.", "danger")
        return redirect(url_for("track_page")) # Or report detail page

    # Determine the current relevant role for escalation
    current_escalation_role = None
    if report.escalated_to_id:
        escalated_user = User.query.get(report.escalated_to_id)
        if escalated_user: current_escalation_role = escalated_user.role
    elif report.assigned_to_id:
        assigned_user = User.query.get(report.assigned_to_id)
        if assigned_user: current_escalation_role = assigned_user.role
    else:
        # If unassigned, maybe default to Operator or base level? Or disallow escalation.
        flash("لا يمكن تصعيد بلاغ غير مسند.", "warning")
        return redirect(url_for("track_page"))
        
    if not current_escalation_role:
         flash("لم يتم العثور على الدور الحالي للبلاغ لتحديد خطوة التصعيد التالية.", "error")
         return redirect(url_for("track_page"))

    # Find the next role in the hierarchy
    next_role = get_next_escalation_role(current_escalation_role)
    if not next_role:
        flash("البلاغ وصل لأعلى مستوى في التصعيد (مدير المشروع).", "info")
        return redirect(url_for("track_page"))

    # Find a user with the next role
    next_user = find_user_with_role(next_role)
    if not next_user:
        flash(f"لم يتم العثور على مستخدم بالدور التالي في التصعيد ({next_role.value}). يرجى التأكد من وجود مستخدمين بهذا الدور.", "warning")
        return redirect(url_for("track_page"))

    # Update report: set escalated_to, status, and log history
    report.escalated_to_id = next_user.id
    report.assigned_to_id = None # Clear direct assignment upon escalation
    report.status = ReportStatus.ESCALATED
    report.add_escalation_step(current_user.id, next_user.id)

    db.session.commit()
    flash(f"تم تصعيد البلاغ بنجاح إلى {next_user.username} ({next_role.value}).", "success")
    return redirect(url_for("track_page"))

@report_actions_bp.route("/<string:report_id>/update_status", methods=["POST"])
@login_required
def update_report_status(report_id):
    report = Report.query.get_or_404(report_id)
    new_status_str = request.form.get("status")

    # Authorization: Check if user can update status (assignee, escalated_to, manager?)
    can_update = False
    if report.assigned_to_id == current_user.id or report.escalated_to_id == current_user.id:
        can_update = True
    # elif current_user.role in [UserRole.SECURITY_MANAGER, UserRole.PROJECT_MANAGER]:
    #    can_update = True
        
    if not can_update:
        flash("ليس لديك الصلاحية لتحديث حالة هذا البلاغ.", "danger")
        return redirect(url_for("track_page"))

    try:
        new_status = ReportStatus(new_status_str)
    except ValueError:
        flash("حالة البلاغ المحددة غير صالحة.", "warning")
        return redirect(url_for("track_page"))

    report.status = new_status
    # Optionally clear assignment/escalation if resolved/closed?
    # if new_status in [ReportStatus.RESOLVED, ReportStatus.CLOSED]:
    #     report.assigned_to_id = None
    #     report.escalated_to_id = None
        
    db.session.commit()
    flash(f"تم تحديث حالة البلاغ إلى 	'{new_status.value}	'.", "success")
    return redirect(url_for("track_page"))

# Add more actions as needed (e.g., add comment, resolve, close)

