# 🍜 回味無窮 — 個人美食地圖與日記

**🌐 線上網站：[https://foodmap-ir9b.onrender.com](https://foodmap-ir9b.onrender.com)**

記下每一口回味無窮的滋味。記錄美食、追蹤每日營養、在地圖上探索台大校園周邊餐廳。

---

## 功能總覽

### 📖 美食日記
- 新增、編輯、刪除用餐紀錄
- 記錄餐廳、餐別、料理類別、消費金額、評分、熱量、蛋白質、心得
- 選擇台大餐廳後**自動帶入地址、菜單、售價、熱量、蛋白質**
- 支援**一次輸入多道菜**，自動加總金額與營養資訊
- 依日期分組顯示，**自動計算每日熱量與蛋白質總計**
- 依關鍵字、料理類別、餐別篩選

### 🗺️ 美食地圖
- 整合 Google Maps，顯示餐廳精確位置（座標來自 Plus Code，精度約 14×14 公尺）
- 依料理類別、價位範圍、距離上限篩選
- **「只顯示我記錄過的餐廳」**快速過濾個人足跡
- 點擊地圖標記查看**所有使用者**的評論（含評分、心得、熱量）
- 飲控模式開啟時右下角顯示**今日熱量／蛋白質進度條**

### 🏪 餐廳資料庫
- 台大校園周邊 **40 間餐廳**、**1,257 道菜單品項**（含售價、熱量、蛋白質）
- 依區域分組（醉月湖旁、第一學生活動中心、鹿鳴廣場等）
- 使用者可自行**新增餐廳**，並刪除自己新增的餐廳
- 展開查看完整菜單

### ⚖️ 飲控設定
- 輸入性別、身高、體重、年齡、活動量，計算 **BMR 與 TDEE**
- 依目標（維持體重 / 增肌 / 減脂）提供每日建議蛋白質攝取量
- 開啟飲控模式後，美食地圖自動篩選健康餐廳

### 👤 使用者系統
- 帳號或 Email 皆可登入
- 美食日記資料各自隔離（只能看到、編輯自己的紀錄）
- 美食地圖可瀏覽所有使用者的公開評論

---

## 技術架構

| 層級 | 技術 |
|------|------|
| 後端框架 | Python 3 / Flask 3.x |
| 資料庫 ORM | Flask-SQLAlchemy 3.x |
| 本機資料庫 | SQLite |
| 正式資料庫 | PostgreSQL（Render） |
| 認證 | bcrypt 密碼雜湊 + Flask session |
| WSGI 伺服器 | Gunicorn |
| 部署平台 | Render |
| 地圖 | Google Maps JavaScript API |
| 座標解碼 | openlocationcode（Plus Code → lat/lng，無需 API） |
| 伺服器端 Geocoding | Google Geocoding API（距離篩選） |

---

## 資料庫結構

```
users          使用者帳號（id, username, email, password_hash）
user_diets     飲控設定（username FK, 身高/體重/年齡, TDEE, 蛋白質目標）
reviews        用餐紀錄（user_id FK, restaurant_id FK, 熱量, 蛋白質 ...）
restaurants    餐廳資料（name, address, plus_code, latitude, longitude ...）
menu_items     菜單品項（restaurant_id FK, 售價, 熱量, 蛋白質）
```

---

## 本機安裝

### 需求
- Python 3.10+

### 步驟

```bash
# 1. 取得程式碼
git clone https://github.com/mandajjf/Food.git
cd Food

# 2. 建立虛擬環境
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# 3. 安裝套件
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 開啟 .env，至少填入 SECRET_KEY

# 5. 啟動
python app.py
```

瀏覽器開啟 `http://localhost:5000`

資料庫（SQLite）會在第一次啟動時自動建立，無需手動執行任何指令。

### 匯入台大餐廳資料（選用）

```bash
python seed.py 餐廳資料資訊庫.xlsx
```

---

## 部署（Render + PostgreSQL）

### 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `SECRET_KEY` | ✅ | Flask session 加密金鑰（建議 32 位隨機字串） |
| `DATABASE_URL` | ✅ | PostgreSQL 連線字串（Render 自動提供） |
| `GOOGLE_MAPS_API_KEY` | 建議 | 地圖顯示與距離篩選 |

產生安全的 SECRET_KEY：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Google Cloud Console 需啟用的 API
- **Maps JavaScript API**（地圖顯示）
- **Geocoding API**（距離篩選時的地址轉座標）

### Build & Start Command

```
Build Command:  pip install -r requirements.txt
Start Command:  gunicorn app:app
```

### 注意事項
- Web Service 閒置 15 分鐘後會休眠，首次請求需約 30 秒喚醒
- 免費 PostgreSQL 有效期限 **90 天**，到期前請備份或升級

---

## 專案結構

```
FoodMap/
├── app.py                  # 主程式：所有路由、API、啟動 migration
├── models.py               # 資料模型（User, UserDiet, Review, Restaurant, MenuItem）
├── database.py             # SQLAlchemy 初始化
├── seed.py                 # 從 Excel 匯入餐廳與菜單資料
├── requirements.txt
├── .env.example
├── static/
│   └── style.css
└── templates/
    ├── base.html           # 共用版面（導覽列）
    ├── dashboard.html      # 首頁（已登入）
    ├── new_review.html     # 新增紀錄
    ├── edit_review.html    # 編輯紀錄
    ├── diary.html          # 美食日記
    ├── food_map.html       # 美食地圖
    ├── restaurants.html    # 餐廳資料庫
    ├── _restaurant_card.html
    ├── diet_setting.html   # 飲控設定
    ├── login.html
    └── sign_up.html
```
