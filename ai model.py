from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 1. 載入資料
iris = load_iris()
X = iris.data           # 花的長度、寬度等特徵
y = iris.target         # 花的種類（0, 1, 2）

# 2. 切分訓練集與測試集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. 建立模型
model = LogisticRegression(max_iter=200)
model.fit(X_train, y_train)

# 4. 預測與評估
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print("預測準確率：", acc)