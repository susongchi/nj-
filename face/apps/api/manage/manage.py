from apps.api import api_bp
from .managefunction import *
from utils import Api, Resource, login_required

api = Api(app=api_bp)

class AdminRegisterApi(Resource):

    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        _return = admin_register_post_f(username=username, password=password)
        return _return
                      
class AdminLoginApi(Resource):

    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        _return = admin_login_post_f(username=username, password=password)
        return _return
                
class AdminLoginStatusApi(Resource):

    def get(self):
        
        _return = admin_login_status_f()
        return _return
        
class FacesApi(Resource):

    @login_required
    def get(self):

        _return = face_f()
        return _return

class CheckNameExists(Resource):

    def get(self):

        _return = check_name_exists_f()
        return _return
        
class GetFaceApi(Resource):

    def get(self):

        _return = get_face_f()
        return _return

class RegisterFaceApi(Resource):

    def post(self):

        _return = register_face_f()
        return _return
    
class DeleteUserApi(Resource):

    @login_required
    def delete(self, user_id):

        _return = delete_user_f(user_id)
        return _return
        
class AllowedUsersByScheduleApi(Resource):

    @login_required
    def post(self):

        _return = allowed_users_by_schedule_f()
        return _return 

class GetSchedules(Resource):

    @login_required
    def get(self):

        _return = get_schedules_f()
        return _return

class DeleteSchedule(Resource):

    @login_required
    def post(self):

        _return = delete_schedule_f()
        return _return
        
class AdminLogout(Resource):

    def post(self):

        _return = admin_logout_f()
        return _return
        
api.add_resource(AdminRegisterApi, "/admin_register")
api.add_resource(AdminLoginApi, "/admin_login")
api.add_resource(AdminLoginStatusApi, "/admin_login_status")
api.add_resource(FacesApi, "faces")
api.add_resource(GetFaceApi, "/get_face")
api.add_resource(RegisterFaceApi, "/register_face")
api.add_resource(DeleteUserApi, "/delete_user/<int:user_id>")
api.add_resource(GetSchedules, "get_schedules")
api.add_resource(AllowedUsersByScheduleApi, "/allowed_users_by_schedule")
api.add_resource(DeleteSchedule, "/delete_schedule")
api.add_resource(AdminLogout, "/admin_logout")
api.add_resource(CheckNameExists, "/check_name_exists")