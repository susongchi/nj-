from apps.api import api_bp
from .reset_passwordfunction import *
from utils.utils import Api, Resource, request

api = Api(app=api_bp)

class ResetPasswordApi(Resource):
    
    def post(self):
        data = request.get_json(force=True)
        uid = data.get("uid")
        token = data.get("token")
        new_password = data.get("new_password")
        
        _return = reset_password_post_f(uid=uid, token=token, new_password=new_password)
        return _return

api.add_resource(ResetPasswordApi, "/reset_password")
