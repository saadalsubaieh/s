# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialize extensions without app instance
db = SQLAlchemy()
login_manager = LoginManager()

# Configure login manager
login_manager.login_view = "user.login" # Use blueprint name and route name
login_manager.login_message = "الرجاء تسجيل الدخول للوصول إلى هذه الصفحة."
login_manager.login_message_category = "info"

