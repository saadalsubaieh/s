# -*- coding: utf-8 -*-
import os
import datetime
from flask import Flask, redirect, url_for
from .config import config # Import config dictionary
from .extensions import db, login_manager # Import initialized extensions

# Import models here to ensure they are known to SQLAlchemy
# It's generally okay here if extensions.py doesn't import from models
from .models.user import User # Needed for user_loader

def create_app(config_name=None):
    """Application Factory Function"""
    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", "default")

    app = Flask(__name__, 
                instance_path=os.path.join(config[config_name].basedir, "instance"),
                static_folder="static", # Standard static folder name
                template_folder="templates" # Standard template folder name
                )
    
    # Load configuration
    app.config.from_object(config[config_name])
    print(f"Loaded config: {config_name}")
    print(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"Upload Folder: {app.config.get('UPLOAD_FOLDER')}")
    print(f"Instance Path: {app.instance_path}")

    # Initialize extensions with the app instance
    db.init_app(app)
    login_manager.init_app(app)
    print("Initialized extensions.")

    # Ensure upload and instance directories exist
    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        os.makedirs(app.instance_path, exist_ok=True)
        print("Upload and instance directories ensured.")
    except OSError as e:
        print(f"Error creating directories: {e}")

    # --- Flask-Login User Loader ---
    @login_manager.user_loader
    def load_user(user_id):
        # Ensure this queries the correct User model
        return User.query.get(int(user_id))

    # --- Context Processor ---
    @app.context_processor
    def inject_global_vars():
        from .models.user import UserRole # Import inside function if needed
        from .models.report import Report, ReportStatus # Import inside function
        from flask_login import current_user
        
        assigned_count = 0
        escalated_count = 0
        if current_user.is_authenticated:
            try:
                # Ensure db session is active within context processor
                assigned_count = Report.query.filter_by(assigned_to_id=current_user.id, status=ReportStatus.ASSIGNED).count()
                escalated_count = Report.query.filter_by(escalated_to_id=current_user.id, status=ReportStatus.ESCALATED).count()
            except Exception as e:
                # Log error if query fails in context processor
                app.logger.error(f"Error querying reports for context processor: {e}")
                
        return {
            "current_year": datetime.datetime.now().year,
            "UserRole": UserRole, # Make UserRole enum available in templates
            "assigned_reports_count": assigned_count,
            "escalated_reports_count": escalated_count
        }

    # --- Register Blueprints --- 
    # We will import and register blueprints after migrating them
    from .routes.user import user_bp
    from .routes.report_actions import report_actions_bp
    from .routes.main import main_bp # We'll create this for main routes like index, login, etc.
    
    app.register_blueprint(user_bp, url_prefix="/api/users") # Keep API prefix if desired
    app.register_blueprint(report_actions_bp) # No prefix needed based on original code
    app.register_blueprint(main_bp) # Register main routes
    print("Registered blueprints.")

    # --- Database Initialization Command ---
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables."""
        # No need for app_context() here, Flask CLI handles it
        db.create_all()
        print("Initialized the database.")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Create a default admin user (e.g., Project Manager)."""
        from .models.user import User, UserRole # Import here
        username = "admin"
        email = "admin@diriyah.com"
        password = "password" # Change in production!
        role = UserRole.PROJECT_MANAGER

        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists.")
            return

        admin_user = User(username=username, email=email, role=role)
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user '{username}' created successfully.")

    # --- Simple route for testing --- 
    # @app.route("/hello")
    # def hello():
    #    return "Hello from Factory!"

    return app

