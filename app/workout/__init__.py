from flask import Blueprint

bp = Blueprint('workout-builder', __name__, template_folder='templates')

from app.main import routes