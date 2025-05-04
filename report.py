# -*- coding: utf-8 -*-
import enum
import datetime
import json
from ..extensions import db # Import db from extensions
from .user import User # Import User model

class ReportStatus(enum.Enum):
    RECEIVED = "تم الاستلام"
    ASSIGNED = "تم الإسناد"
    IN_PROGRESS = "قيد المعالجة"
    ESCALATED = "تم التصعيد"
    RESOLVED = "تم الحل"
    CLOSED = "مغلق"

class ReportImportance(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Report(db.Model):
    id = db.Column(db.String(36), primary_key=True) # UUID as string
    reporter_name = db.Column(db.String(100))
    reporter_id = db.Column(db.String(50))
    report_date = db.Column(db.Date)
    location = db.Column(db.String(200), nullable=False)
    location_other = db.Column(db.String(500)) # For 'Other' location details
    report_type = db.Column(db.String(100), nullable=False)
    importance = db.Column(db.Enum(ReportImportance), nullable=False)
    details = db.Column(db.Text, nullable=False)
    action_taken = db.Column(db.Text)
    submission_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    status = db.Column(db.Enum(ReportStatus), nullable=False, default=ReportStatus.RECEIVED)
    
    # Foreign key for the user the report is currently assigned to
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    # --- Corrected Relationship using back_populates ---
    assignee = db.relationship(
        "User", 
        foreign_keys=[assigned_to_id], 
        back_populates="assigned_reports" # Connects to assigned_reports in User
    )
    # ----------------------------------------------------

    # Foreign key for the user the report is currently escalated to
    escalated_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    # --- Corrected Relationship using back_populates ---
    escalated_to_user = db.relationship(
        "User", 
        foreign_keys=[escalated_to_id], 
        back_populates="escalated_reports" # Connects to escalated_reports in User
    )
    # ----------------------------------------------------

    # Store image filenames as a JSON list or comma-separated string
    images = db.Column(db.Text) # Store as JSON string or comma-separated

    # Escalation History (Store as JSON or separate table if complex)
    escalation_history = db.Column(db.Text) # Simple JSON: [{"from_user_id": id, "to_user_id": id, "timestamp": ts}, ...]

    def __repr__(self):
        return f"<Report {self.id} - {self.report_type}>"

    def set_images(self, image_list):
        self.images = json.dumps(image_list)

    def get_images(self):
        try:
            return json.loads(self.images) if self.images else []
        except json.JSONDecodeError:
            return [] # Return empty list if JSON is invalid

    def add_escalation_step(self, from_user_id, to_user_id):
        history = self.get_escalation_history()
        history.append({
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        self.escalation_history = json.dumps(history)

    def get_escalation_history(self):
        try:
            return json.loads(self.escalation_history) if self.escalation_history else []
        except json.JSONDecodeError:
            return []

