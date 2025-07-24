from apps.api import api_bp
from .registerfunction import *
from utils.utils import Api, Resource

api = Api(app=api_bp)

class RegisterApi(Resource):

    def post(self):

        _return = register_f()
        return _return

    
api.add_resource(RegisterApi, "/register")