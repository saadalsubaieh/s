# -*- coding: utf-8 -*-
import os
import sys

# Add the project directory to the sys.path
project_home = os.path.dirname(__file__)
sys.path.insert(0, project_home)

# Import the factory function
from src import create_app

# Create the Flask app instance using the factory
# You might want to pass 'production' when deploying to PythonAnywhere
# config_name = os.getenv('FLASK_CONFIG', 'production') 
application = create_app() # Defaults to 'development' or 'default' based on FLASK_CONFIG

# Optional: Add code to create DB tables if they don't exist (useful for initial setup)
# with application.app_context():
#    from src.extensions import db
#    db.create_all()

