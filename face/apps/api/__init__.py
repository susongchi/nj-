from flask import Blueprint

api_bp = Blueprint("apis", __name__, url_prefix="/")

from apps.api.manage import manage
from apps.api.login import login
from apps.api.register import register
from apps.api.resetpassword import rest_password