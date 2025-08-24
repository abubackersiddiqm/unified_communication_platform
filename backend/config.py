# -----------------------------------------------------------------------------
# Project: Unified Communication Platform
# Author: Abubacker Siddiq M
# Copyright (c) 2025 Abubacker Siddiq M
# License: MIT License (See LICENSE file for details)
# -----------------------------------------------------------------------------

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL'
    ) or 'sqlite:///ucp.db'

    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # WebRTC configuration
    WEBRTC_ICE_SERVERS = os.environ.get(
        'WEBRTC_ICE_SERVERS',
        'stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302'
    )


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class DemoConfig(Config):
    """Demo configuration"""
    DEBUG = True
    FLASK_ENV = 'demo'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'demo': DemoConfig,
    'default': DevelopmentConfig
}
