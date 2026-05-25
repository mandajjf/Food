# 🍜 回味無窮 — 個人美食地圖與日記

把每一口難忘的美食記錄下來，打造專屬於你的美食日記與地圖。

---

## 📌 專案介紹

「回味無窮」是一個個人美食記錄平台，讓你可以：
- 記錄每次用餐的餐廳、日期、評分、心得
- 瀏覽、搜尋、篩選自己的所有美食紀錄
- 查看有地址的餐廳清單，一鍵在 Google Maps 開啟

---

## ✅ 目前功能

- 使用者註冊、登入、登出
- 新增美食紀錄（餐廳名稱、日期、餐別、類別、價格、評分、心得、地址）
- 查看美食日記（依日期排序）
- 依關鍵字、類別、餐別篩選紀錄
- 編輯、刪除自己的紀錄
- 美食地圖（有地址的餐廳清單＋Google Maps 連結）
- 使用者資料隔離：只能看到、編輯自己的紀錄

---

## 🛠️ 技術棧

| 層級 | 技術 |
|------|------|
| 後端框架 | Python / Flask |
| 模板引擎 | Jinja2 |
| 資料庫（本機） | SQLite |
| 資料庫（正式） | PostgreSQL（Render） |
| ORM | Flask-SQLAlchemy |
| 密碼雜湊 | bcrypt |
| 環境變數 | python-dotenv |
| WSGI 伺服器 | gunicorn |
| 前端 | HTML + CSS（無前端框架） |

---

## 📁 專案結構

```
FoodMap/
├── app.py              # Flask 主程式（所有路由）
├── models.py           # SQLAlchemy 資料模型（User, Review）
├── database.py         # db = SQLAlchemy() 初始化
├── requirements.txt    # Python 套件清單
├── render.yaml         # Render 部署設定
├── .env.example        # 環境變數範例
├── .gitignore
├── README.md
├── instance/           # SQLite 資料庫（本機，不上傳 git）
├── static/
│   └── style.css
└── templates/
    ├── base.html       # 共用版型
    ├── index.html      # 首頁
    ├── login.html      # 登入
    ├── sign_up.html    # 註冊
    ├── dashboard.html  # 儀表板
    ├── new_review.html # 新增紀錄
    ├── diary.html      # 美食日記
    ├── edit_review.html# 編輯紀錄
    └── food_map.html   # 美食地圖
```

---

## 🚀 本機安裝方式

### 1. 進入專案目錄

```bash
cd FoodMap
```

### 2. 建立虛擬環境並啟動

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. 安裝套件

```bash
pip install -r requirements.txt
```

### 4. 設定環境變數

複製範例並編輯：

```bash
cp .env.example .env
```

編輯 `.env`，至少設定 `SECRET_KEY`：

```
SECRET_KEY=任意一組隨機長字串
```

本機開發**不需要**設定 `DATABASE_URL`，程式會自動使用 SQLite。

---

## 🗄️ 資料庫初始化

資料庫會在**第一次啟動時自動建立**（`db.create_all()`）。

- 本機：在 `instance/app.db` 建立 SQLite 資料庫
- Render：在 PostgreSQL 建立所有資料表

無需手動執行任何指令。

---

## ▶️ 本機啟動網站

```bash
python app.py
```

瀏覽器開啟 http://127.0.0.1:5000

---

## 👤 如何使用

### 註冊

1. 點擊首頁「立即免費加入」
2. 填入使用者名稱、Email、密碼（至少 6 碼）
3. 確認密碼一致後送出
4. 系統導向登入頁

### 登入

- 使用**使用者名稱**或 **Email** 搭配密碼登入

### 新增美食紀錄

1. 登入後點擊「新增紀錄」
2. 填入餐廳名稱（必填）、日期（必填）、及其他欄位
3. 填入地址後可在美食地圖顯示

### 查看 / 篩選紀錄

- 點擊「美食日記」查看所有紀錄
- 可依關鍵字、類別、餐別篩選

### 編輯 / 刪除紀錄

- 在日記頁每筆紀錄右下角點擊「編輯」或「刪除」

---

## ☁️ 部署到 Render

### 前置條件

- 已有 [Render](https://render.com) 帳號
- 專案已推送到 GitHub

### 步驟一：推送程式碼到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的帳號/FoodMap.git
git push -u origin main
```

### 步驟二：在 Render 建立 PostgreSQL 資料庫

1. 登入 Render Dashboard
2. 點擊 **New → PostgreSQL**
3. 填入名稱（例：`foodmap-db`），選擇 **Free** 方案
4. 點擊 **Create Database**
5. 建立後記錄 **Internal Database URL**（格式：`postgresql://...`）

### 步驟三：建立 Web Service

1. 點擊 **New → Web Service**
2. 連接你的 GitHub repo
3. 填入以下設定：

| 欄位 | 值 |
|------|----|
| Environment | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |

### 步驟四：設定環境變數

在 Web Service 的 **Environment** 頁面新增：

| 變數名稱 | 值 |
|----------|----|
| `SECRET_KEY` | 一組隨機長字串（可用 `python -c "import secrets; print(secrets.token_hex(32))"` 產生） |
| `DATABASE_URL` | 步驟二取得的 Internal Database URL |

> ⚠️ **重要**：`DATABASE_URL` 請使用 **Internal Database URL**，不要用 External URL，可以節省費用且更安全。

### 步驟五：部署

點擊 **Deploy** 後等待約 2–3 分鐘，部署完成後即可使用。

---

## 🔧 使用 render.yaml 自動部署（Blueprint）

本專案已包含 `render.yaml`，可直接使用 Render Blueprint 一鍵建立 Web Service + PostgreSQL：

1. Render Dashboard → **New → Blueprint**
2. 連接你的 GitHub repo
3. Render 會自動讀取 `render.yaml` 並建立所有服務

> ⚠️ Free 方案的 PostgreSQL 在 `render.yaml` 中設定為 `plan: free`，但 Render 免費 PostgreSQL 有 90 天有效期限，到期後需手動升級。

---

## ⚙️ 環境變數說明

| 變數 | 必填 | 說明 |
|------|------|------|
| `SECRET_KEY` | 是（正式環境） | Flask session 加密金鑰，正式環境務必設定為隨機長字串 |
| `DATABASE_URL` | 正式環境必填 | PostgreSQL 連線字串；未設定時使用本機 SQLite |
| `FLASK_ENV` | 否 | `development` 或 `production`（預設 production） |
| `GOOGLE_MAPS_API_KEY` | 否 | 未來整合 Google Maps API 時使用 |

---

## ⚠️ Render 免費方案限制

| 項目 | 限制 |
|------|------|
| Web Service | 閒置 15 分鐘後會休眠，首次請求需約 30 秒喚醒 |
| PostgreSQL | 免費方案有效期限 **90 天**，到期後資料庫會被刪除 |
| PostgreSQL 容量 | 免費方案 1 GB |

> **建議**：正式長期使用請升級為付費方案（PostgreSQL 月費約 $7 USD）。  
> **切勿**在 Render 上使用 SQLite 作為正式資料庫——Render 的檔案系統是暫時性的，重新部署後資料會消失。

---

## 🗺️ 未來功能規劃

- [ ] 整合 Google Maps API，在地圖上標示餐廳位置
- [ ] 上傳用餐照片
- [ ] 消費統計分析（月均消費、最常去的類別）
- [ ] 匯出 CSV / PDF 報表
- [ ] 公開分享特定紀錄給朋友
- [ ] 設定「想去清單」（Wish List）
- [ ] 飲控模式（記錄卡路里）
- [ ] 手機 App（PWA）

---

## 🔑 如何產生安全的 SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

將輸出結果填入 `.env` 的 `SECRET_KEY`。
