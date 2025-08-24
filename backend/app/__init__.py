# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_cors import CORS
from flask_mail import Mail
from flask_bcrypt import Bcrypt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
migrate = Migrate()
mail = Mail()
bcrypt = Bcrypt()


def create_app(config_name='development'):
    app = Flask(__name__)

    # Load configuration
    from config import config
    app.config.from_object(config[config_name])

    # Mail configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get(
        'MAIL_USE_TLS',
        'true'
    ).lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    migrate.init_app(app, db)
    mail.init_app(app)
    bcrypt.init_app(app)
    CORS(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from .auth import auth_bp
    from .main import main_bp
    from .admin import admin_bp
    from .api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Import models to ensure they are registered with SQLAlchemy
    from .models import (
        User, Role, Call, Chat, Voicemail, Contact,
        InternationalRate, SIPTrunk
    )

    # Create database tables
    with app.app_context():
        db.create_all()

        # Create default roles if they don't exist
        if not Role.query.first():
            admin_role = Role(
                name='Admin',
                description='System Administrator'
            )
            agent_role = Role(
                name='Agent',
                description='Customer Service Agent'
            )
            user_role = Role(
                name='User',
                description='Regular User'
            )

            db.session.add(admin_role)
            db.session.add(agent_role)
            db.session.add(user_role)
            db.session.commit()
        admin_role = Role.query.filter_by(name='Admin').first()

        # Create demo admin user if not exists
        if not User.query.filter_by(username='demo').first():
            demo_user = User(
                username='demo',
                email='demo@example.com',
                first_name='Demo',
                last_name='Admin'
            )
            demo_user.set_password('demo123')
            demo_user.roles.append(admin_role)  # Assign Admin role
            db.session.add(demo_user)
            db.session.commit()

        # Create sample international rates if they don't exist
        if not InternationalRate.query.first():
            india_rate = InternationalRate(
                country_code='+91',
                country_name='India',
                rate_per_minute=0.0250
            )
            us_rate = InternationalRate(
                country_code='+1',
                country_name='United States/Canada',
                rate_per_minute=0.0150
            )
            uk_rate = InternationalRate(
                country_code='+44',
                country_name='United Kingdom',
                rate_per_minute=0.0200
            )
            australia_rate = InternationalRate(
                country_code='+61',
                country_name='Australia',
                rate_per_minute=0.0300
            )

            db.session.add(india_rate)
            db.session.add(us_rate)
            db.session.add(uk_rate)
            db.session.add(australia_rate)
            db.session.commit()

    return app
