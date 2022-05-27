"""
Flask app initialiser
"""

from json import tool
import os
from flask import Flask

from elasticsearch import Elasticsearch
from flask_bootstrap import Bootstrap5
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

# Set a project base directory variable
baseDir = os.path.abspath(os.path.dirname(__file__))

bootstrap = Bootstrap5()
db = SQLAlchemy()
login = LoginManager()
mail = Mail()
migrate = Migrate()
toolbar = DebugToolbarExtension()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    bootstrap.init_app(app)
    db.init_app(app)
    login.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    toolbar.init_app(app)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.workout_builder import bp as wb_bp
    app.register_blueprint(wb_bp)

    return app

from app import models