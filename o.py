import requests

url = 'https://github.com/DefTruth/yolov5-face/releases/download/v0.0/yolov8n-face.pt'
filename = 'yolov8n-face.pt'

print(f"📥 正在下載 {filename} ...")
response = requests.get(url)
with open(filename, 'wb') as f:
    f.write(response.content)
print("✅ 下載完成！")