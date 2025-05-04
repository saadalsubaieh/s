# -*- coding: utf-8 -*-
import enum
# Remove: from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from ..extensions import db # Import db from extensions

# Remove: Define db here, so it can be imported by other models
# Remove: db = SQLAlchemy()

class UserRole(enum.Enum):
    OPERATOR = "مشغل غرفة تحكم"
    SUPERVISOR = "مشرف غرفة تحكم"
    QUALITY = "اخصائي جودة"
    SECURITY_MANAGER = "مدير امن"
    PROJECT_MANAGER = "مدير مشروع"
    REPORTS_SPECIALIST = "اخصائي تقارير"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.OPERATOR)
    
    # --- Corrected Relationships using back_populates ---
    # Relationship to reports assigned to this user
    assigned_reports = db.relationship(
        'Report', 
        foreign_keys='Report.assigned_to_id', 
        back_populates='assignee', # Changed from backref
        lazy=True
    )
    # Relationship to reports escalated to this user
    escalated_reports = db.relationship(
        'Report', 
        foreign_keys='Report.escalated_to_id', 
        back_populates='escalated_to_user', # Changed from backref
        lazy=True
    )
    # ----------------------------------------------------

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value
        }

