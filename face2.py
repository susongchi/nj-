from flask import Flask, render_template_string, request, jsonify
import cv2
import face_recognition
import numpy as np
import os
import base64

app = Flask(__name__)

REGISTERED_DIR = "static/registered_faces"

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>臉部登入系統</title>
</head>
<body>
  <h2>臉部登入系統</h2>
  <form id="loginForm">
    姓名：<input type="text" id="name" required>
    <button type="submit">開始登入</button>
  </form>

  <div id="camera" style="display:none;">
    <video id="video" width="320" height="240" autoplay></video>
  </div>

  <div id="result"></div>

<script>
const video = document.getElementById('video');
const cameraDiv = document.getElementById('camera');
const resultDiv = document.getElementById('result');
const form = document.getElementById('loginForm');

form.onsubmit = e => {
  e.preventDefault();
  const name = document.getElementById('name').value.trim();
  if (!name) {
    alert('請輸入姓名');
    return;
  }
  cameraDiv.style.display = 'block';
  startCameraAndCapture(name);
};

function startCameraAndCapture(name) {
  navigator.mediaDevices.getUserMedia({video:true})
    .then(stream => {
      video.srcObject = stream;

      // 等待攝影機畫面穩定 1 秒後自動截圖
      setTimeout(() => {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL('image/jpeg');

        // 停止攝影機
        stream.getTracks().forEach(track => track.stop());

        // 發送影像比對請求
        fetch('/verify', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({name: name, image: dataUrl})
        })
        .then(res => res.json())
        .then(data => {
          if(data.status === 'success'){
            resultDiv.innerHTML = `<p style="color:green;">認證成功！相似度：${(data.similarity*100).toFixed(2)}%</p>`;
          } else {
            resultDiv.innerHTML = `<p style="color:red;">認證失敗：${data.message}</p>`;
          }
        })
        .catch(err => {
          resultDiv.innerHTML = `<p style="color:red;">錯誤：${err}</p>`;
        });

      }, 1000); // 1 秒延遲拍照
    })
    .catch(err => {
      alert('無法開啟攝影機: ' + err);
    });
}
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json()
    name = data.get('name')
    image_data = data.get('image')

    if not name or not image_data:
        return jsonify({"status": "fail", "message": "缺少姓名或影像資料"}), 400

    registered_path = os.path.join(REGISTERED_DIR, f"{name}.jpg")
    if not os.path.exists(registered_path):
        return jsonify({"status": "fail", "message": "找不到該姓名的註冊資料"}), 404

    # 解碼 base64 image
    header, encoded = image_data.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Encode 註冊臉部
    reg_img = face_recognition.load_image_file(registered_path)
    reg_encodings = face_recognition.face_encodings(reg_img)
    if not reg_encodings:
        return jsonify({"status": "fail", "message": "註冊臉部照片無法辨識"}), 400
    reg_encoding = reg_encodings[0]

    # Encode 拍攝影像
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    live_encodings = face_recognition.face_encodings(img_rgb)
    if not live_encodings:
        return jsonify({"status": "fail", "message": "無法從攝影機影像中偵測到臉部"}), 400
    live_encoding = live_encodings[0]

    # 計算相似度
    distance = face_recognition.face_distance([reg_encoding], live_encoding)[0]
    similarity = 1 - distance
    threshold = 0.5

    if distance < threshold:
        return jsonify({"status": "success", "similarity": similarity})
    else:
        return jsonify({"status": "fail", "message": "人臉不匹配"})

if __name__ == '__main__':
    app.run(debug=True)
