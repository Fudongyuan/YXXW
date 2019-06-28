from flask import Blueprint

passport_blueprint = Blueprint('passport', __name__, url_prefix='/passport')
from . import views
