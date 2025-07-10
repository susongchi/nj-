import os
from flask import Flask, render_template_string, request, make_response, send_from_directory

app = Flask(__name__)

_user = [
    {"name": "user1", "username": "name1", "password": "1234"},
    {"name": "user2", "username": "name2", "password": "12345"}
]
# _username = "name"
# _password = "1234"
@app.route("/login", methods=["GET", "POST"])
def login():
    _username = ""
    _password = ""
    _data = ""
    message = ""
    status_code = 200

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # 搜尋使用者帳號
        for user in _user:
            if user["username"] == username:
                _username = user["username"]
                _password = user["password"]
                _data = {'name': user['name'], 'imageUrl': f'http://192.168.1.133:5000/image?username={user["username"]}'}
                break
        # 帳號不存在    
        if _username == "":
            message = "帳號不存在"
            status_code = 404

        # 驗證密碼
        try:
            if username != _username:
                message = "帳號錯誤"
                status_code = 403
            elif password != _password:
                message = "密碼錯誤"
                status_code = 403
            else:
                message = "登入成功"
                status_code = 200
        except Exception as e:
            message = "登入失敗"
            status_code = 401
    # response= make_response(render_template_string(HTML, massage=message))
    response = {'message': message, 'data': _data}, status_code
    return response


@app.route("/image", methods=["GET", "POST"])
def image():
    if request.method == "POST":
        username = request.form.get("username")
        file = request.files.get("file")
        if file:
            filename = f"{username}.jpg"
            upload_folder = "uploads"
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join("uploads", filename)
            file.save(file_path)
            return make_response(f"File {filename} uploaded successfully.", 200)
        else:
            return make_response("No file uploaded.", 400)
    
    if request.method == "GET":
        username = request.args.get("username")
        print(username)
        if not username:
            return {'message': 'Username is required.'}, 400
        
        return send_from_directory("C:/Users/x1206/nj-/uploads", f'{username}.jpg')
    # response = {'message': message, 'data': _data}, status_code
    # # return response
        
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)