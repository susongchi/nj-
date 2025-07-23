from apps.api import api_bp
from .loginfunction import *
from utils import Resource, Api

api = Api(app=api_bp)

class CurrentMeetingApi(Resource):

    def get(self):

        _return = current_meeting_f()
        return _return

class LoginStatusApi(Resource):

    def get(self):

        _return = login_status_f()
        return _return 
            
class AutoVerifyApi(Resource):

    def post(self):

        _return = auto_verify_f()
        return _return

api.add_resource(AutoVerifyApi, "/auto_verify")
api.add_resource(LoginStatusApi, "/login_status")
api.add_resource(CurrentMeetingApi, "/current_meeting")