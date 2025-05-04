# -*- coding: utf-8 -*-
import os

class Config:
    # Define the base directory of the application *inside* the class
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.abspath(os.path.join(basedir, "uploads"))
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    MAX_IMAGES = 20
    # Default to SQLite for simplicity and compatibility with PythonAnywhere free tier
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "app.db"))

class DevelopmentConfig(Config):
    DEBUG = True
    # You might want a different DB for development if needed
    # SQLALCHEMY_DATABASE_URI = "sqlite:///dev.db"

class ProductionConfig(Config):
    DEBUG = False
    # Ensure DATABASE_URL environment variable is set in production (e.g., on PythonAnywhere)
    # Example for MySQL on PythonAnywhere (adjust username, password, host, dbname):
    # SQLALCHEMY_DATABASE_URI = "mysql+pymysql://username:password@username.mysql.pythonanywhere-services.com/dbname"

# Dictionary to access config classes by name
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

