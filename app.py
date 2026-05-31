import os
from functools import wraps
from datetime import date, datetime
import math

import bcrypt
import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

load_dotenv()

from database import db
from models import MenuItem, Restaurant, Review, User, UserDiet

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Secret key
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION")
api_key = os.environ.get("GOOGLE_MAPS_API_KEY")

# Database configuration
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url:
    # Render provides postgres:// but SQLAlchemy 1.4+ requires postgresql://
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = _db_url
else:
    _basedir = os.path.abspath(os.path.dirname(__file__))
    _instance_path = os.path.join(_basedir, "instance")
    os.makedirs(_instance_path, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{os.path.join(_instance_path, 'app.db')}"
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Auto-create tables on startup (safe: skips existing tables)
with app.app_context():
    db.create_all()
    # Add new columns if they don't exist yet (idempotent migration)
    def _add_column_if_missing(conn, table, column, col_type):
        try:
            conn.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()
        except Exception as e:
            msg = str(e).lower()
            if "duplicate column" not in msg and "already exists" not in msg:
                raise
            conn.rollback()

    with db.engine.connect() as _conn:
        _add_column_if_missing(_conn, "reviews",     "calories",   "FLOAT")
        _add_column_if_missing(_conn, "reviews",     "protein",    "FLOAT")
        _add_column_if_missing(_conn, "restaurants", "created_by", "INTEGER")
        _add_column_if_missing(_conn, "restaurants", "is_seeded",  "BOOLEAN DEFAULT FALSE")
        # 將 seed 匯入的餐廳（created_by IS NULL）標記為 is_seeded = TRUE
        try:
            _conn.execute(db.text(
                "UPDATE restaurants SET is_seeded = TRUE "
                "WHERE created_by IS NULL AND (is_seeded IS NULL OR is_seeded = FALSE)"
            ))
            _conn.commit()
        except Exception:
            _conn.rollback()
        # 修正欄位拼字錯誤：acticity_coeff → activity_coeff
        try:
            _conn.execute(db.text(
                "ALTER TABLE user_diets RENAME COLUMN acticity_coeff TO activity_coeff"
            ))
            _conn.commit()
        except Exception:
            _conn.rollback()
        # 統一料理類別：日記選項與餐廳 cuisine_style 對齊
        try:
            _conn.execute(db.text("UPDATE reviews SET category = '西餐' WHERE category IN ('義式', '美式')"))
            _conn.execute(db.text("UPDATE reviews SET category = '中餐' WHERE category IN ('台式', '韓式')"))
            _conn.execute(db.text("UPDATE reviews SET category = '點心' WHERE category = '飲料'"))
            _conn.execute(db.text("UPDATE restaurants SET category = '西餐' WHERE category IN ('義式', '美式')"))
            _conn.commit()
        except Exception:
            _conn.rollback()


# ---------------------------------------------------------------------------
# Custom Jinja2 filter
# ---------------------------------------------------------------------------

@app.template_filter("format_price")
def format_price(price):
    if price is None:
        return "—"
    if price == int(price):
        return f"NT${int(price):,}"
    return f"NT${price:,.2f}"


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("請先登入才能使用此功能。", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# ── 註冊 ──────────────────────────────────────────────────────────────────

@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []

        if not username:
            errors.append("使用者名稱不可空白。")
        if not email:
            errors.append("Email 不可空白。")
        elif "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Email 格式不正確。")
        if not password:
            errors.append("密碼不可空白。")
        elif len(password) < 6:
            errors.append("密碼長度至少 6 碼。")
        if password != confirm_password:
            errors.append("密碼與確認密碼不一致。")

        if not errors:
            if User.query.filter_by(username=username).first():
                errors.append("此使用者名稱已被使用。")
            if User.query.filter_by(email=email).first():
                errors.append("此 Email 已被其他帳號使用。")

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template("sign_up.html", username=username, email=email)

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()

        flash("註冊成功！請登入。", "success")
        return redirect(url_for("login"))

    return render_template("sign_up.html")


# ── 登入 ──────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("請輸入帳號與密碼。", "danger")
            return render_template("login.html", identifier=identifier)

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        ):
            session["user_id"] = user.id
            session["username"] = user.username
            diet_entry = UserDiet.query.filter_by(username=user.username).first()
            session["diet_mode"] = bool(diet_entry and diet_entry.diet_mode)
            flash(f"歡迎回來，{user.username}！", "success")
            return redirect(url_for("dashboard"))

        flash("帳號或密碼錯誤，請重試。", "danger")
        return render_template("login.html", identifier=identifier)

    return render_template("login.html")


# ── 登出 ──────────────────────────────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    flash("已成功登出，下次再來！", "info")
    return redirect(url_for("index"))


# ── 首頁 ────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    review_count = Review.query.filter_by(user_id=session["user_id"]).count()
    return render_template("dashboard.html", review_count=review_count)


# ── 新增紀錄 ──────────────────────────────────────────────────────────────

MEAL_TYPES = ["早餐", "午餐", "晚餐", "點心"]
CATEGORIES = ["中餐", "日式", "西餐", "甜點", "點心", "其他"]


@app.route("/new_review", methods=["GET", "POST"])
@login_required
def new_review():
    if request.method == "POST":
        restaurant_name = request.form.get("restaurant_name", "").strip()
        visit_date_str = request.form.get("visit_date", "").strip()
        meal_type = request.form.get("meal_type", "").strip()
        category = request.form.get("category", "").strip()
        price_str    = request.form.get("price",    "").strip()
        rating_str   = request.form.get("rating",   "").strip()
        calories_str = request.form.get("calories", "").strip()
        protein_str  = request.form.get("protein",  "").strip()
        comment = request.form.get("comment", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        visit_date = None
        price = rating = calories = protein = None

        if not restaurant_name:
            errors.append("餐廳名稱為必填。")

        if not visit_date_str:
            errors.append("用餐日期為必填。")
        else:
            try:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append("日期格式不正確，請使用 YYYY-MM-DD。")

        if price_str:
            try:
                price = float(price_str)
                if price < 0:
                    errors.append("價格不可為負數。")
            except ValueError:
                errors.append("價格必須為數字。")

        if rating_str:
            try:
                rating = int(rating_str)
                if not 1 <= rating <= 5:
                    errors.append("評分必須在 1 到 5 之間。")
            except ValueError:
                errors.append("評分必須為整數。")

        if calories_str:
            try:
                calories = float(calories_str)
                if calories < 0:
                    errors.append("熱量不可為負數。")
            except ValueError:
                errors.append("熱量必須為數字。")

        if protein_str:
            try:
                protein = float(protein_str)
                if protein < 0:
                    errors.append("蛋白質不可為負數。")
            except ValueError:
                errors.append("蛋白質必須為數字。")

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "new_review.html",
                meal_types=MEAL_TYPES,
                categories=CATEGORIES,
                form=request.form,
            )

        review = Review(
            user_id=session["user_id"],
            restaurant_name=restaurant_name,
            visit_date=visit_date,
            meal_type=meal_type or None,
            category=category or None,
            price=price,
            rating=rating,
            comment=comment or None,
            address=address or None,
            calories=calories,
            protein=protein,
        )
        db.session.add(review)

        # 若餐廳不在資料庫中，自動建立一筆基本紀錄
        if not Restaurant.query.filter_by(name=restaurant_name).first():
            db.session.add(Restaurant(
                name=restaurant_name,
                address=address or None,
                created_by=session["user_id"],
            ))

        db.session.commit()

        flash("美食紀錄新增成功！", "success")
        return redirect(url_for("diary"))

    restaurant_names = [
        r.name for r in Restaurant.query.order_by(Restaurant.name).all()
    ]
    return render_template(
        "new_review.html",
        meal_types=MEAL_TYPES,
        categories=CATEGORIES,
        form={"visit_date": date.today().isoformat()},
        restaurant_names=restaurant_names,
    )


# ── 美食日記 ──────────────────────────────────────────────────────────────

@app.route("/diary")
@login_required
def diary():
    keyword = request.args.get("keyword", "").strip()
    filter_category = request.args.get("category", "").strip()
    filter_meal_type = request.args.get("meal_type", "").strip()

    query = Review.query.filter_by(user_id=session["user_id"])

    if keyword:
        query = query.filter(
            (Review.restaurant_name.ilike(f"%{keyword}%"))
            | (Review.comment.ilike(f"%{keyword}%"))
        )
    if filter_category:
        query = query.filter_by(category=filter_category)
    if filter_meal_type:
        query = query.filter_by(meal_type=filter_meal_type)

    reviews = query.order_by(
        Review.visit_date.desc(), Review.created_at.desc()
    ).all()

    # 依日期分組，計算每日總計
    from collections import OrderedDict
    grouped = OrderedDict()
    for r in reviews:
        grouped.setdefault(r.visit_date, []).append(r)

    grouped_days = []
    for d, day_reviews in grouped.items():
        total_cal = sum(r.calories for r in day_reviews if r.calories)
        total_pro = sum(r.protein  for r in day_reviews if r.protein)
        grouped_days.append({
            "date":           d,
            "reviews":        day_reviews,
            "total_calories": round(total_cal) if total_cal else None,
            "total_protein":  round(total_pro, 1) if total_pro else None,
        })

    return render_template(
        "diary.html",
        grouped_days=grouped_days,
        total_reviews=len(reviews),
        keyword=keyword,
        filter_category=filter_category,
        filter_meal_type=filter_meal_type,
        categories=CATEGORIES,
        meal_types=MEAL_TYPES,
    )


# ── 編輯紀錄 ──────────────────────────────────────────────────────────────

@app.route("/review/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_review(id):
    review = Review.query.get_or_404(id)

    if review.user_id != session["user_id"]:
        flash("您沒有權限編輯此紀錄。", "danger")
        return redirect(url_for("diary"))

    if request.method == "POST":
        restaurant_name = request.form.get("restaurant_name", "").strip()
        visit_date_str = request.form.get("visit_date", "").strip()
        meal_type = request.form.get("meal_type", "").strip()
        category = request.form.get("category", "").strip()
        price_str    = request.form.get("price",    "").strip()
        rating_str   = request.form.get("rating",   "").strip()
        calories_str = request.form.get("calories", "").strip()
        protein_str  = request.form.get("protein",  "").strip()
        comment = request.form.get("comment", "").strip()
        address = request.form.get("address", "").strip()

        errors = []
        visit_date = None
        price = rating = calories = protein = None

        if not restaurant_name:
            errors.append("餐廳名稱為必填。")

        if not visit_date_str:
            errors.append("用餐日期為必填。")
        else:
            try:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append("日期格式不正確。")

        if price_str:
            try:
                price = float(price_str)
                if price < 0:
                    errors.append("價格不可為負數。")
            except ValueError:
                errors.append("價格必須為數字。")

        if rating_str:
            try:
                rating = int(rating_str)
                if not 1 <= rating <= 5:
                    errors.append("評分必須在 1 到 5 之間。")
            except ValueError:
                errors.append("評分必須為整數。")

        if calories_str:
            try:
                calories = float(calories_str)
                if calories < 0:
                    errors.append("熱量不可為負數。")
            except ValueError:
                errors.append("熱量必須為數字。")

        if protein_str:
            try:
                protein = float(protein_str)
                if protein < 0:
                    errors.append("蛋白質不可為負數。")
            except ValueError:
                errors.append("蛋白質必須為數字。")

        if errors:
            for msg in errors:
                flash(msg, "danger")
            return render_template(
                "edit_review.html",
                review=review,
                meal_types=MEAL_TYPES,
                categories=CATEGORIES,
            )

        review.restaurant_name = restaurant_name
        review.visit_date = visit_date
        review.meal_type = meal_type or None
        review.category = category or None
        review.price = price
        review.rating = rating
        review.comment = comment or None
        review.address = address or None
        review.calories = calories
        review.protein = protein
        review.updated_at = datetime.utcnow()

        # 若餐廳不在資料庫中，自動建立一筆基本紀錄
        if not Restaurant.query.filter_by(name=restaurant_name).first():
            db.session.add(Restaurant(
                name=restaurant_name,
                address=address or None,
                created_by=session["user_id"],
            ))

        db.session.commit()

        flash("紀錄更新成功！", "success")
        return redirect(url_for("diary"))

    restaurant_names = [
        r.name for r in Restaurant.query.order_by(Restaurant.name).all()
    ]
    return render_template(
        "edit_review.html",
        review=review,
        meal_types=MEAL_TYPES,
        categories=CATEGORIES,
        restaurant_names=restaurant_names,
    )


# ── 刪除紀錄 ──────────────────────────────────────────────────────────────

@app.route("/review/<int:id>/delete", methods=["POST"])
@login_required
def delete_review(id):
    review = Review.query.get_or_404(id)

    if review.user_id != session["user_id"]:
        flash("您沒有權限刪除此紀錄。", "danger")
        return redirect(url_for("diary"))

    db.session.delete(review)
    db.session.commit()

    flash("紀錄已成功刪除。", "success")
    return redirect(url_for("diary"))


# ── 美食地圖 ──────────────────────────────────────────────────────────────

@app.route("/food_map")
@login_required
def food_map():
    # 從 DB 動態取得所有 cuisine_style 值
    raw = db.session.query(Restaurant.cuisine_style).distinct().all()
    cuisine_styles = sorted(
        [r[0] for r in raw if r[0]],
        key=lambda x: x
    )
    return render_template(
        "food_map.html",
        api_key=api_key,
        cuisine_styles=cuisine_styles,
    )

def haversine_distance(lat1, lon1, lat2, lon2):
    """計算兩點之間的距離（公里），使用 Haversine 公式"""
    R = 6371  # 地球半徑（公里）
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@app.route("/api/restaurants", methods=["POST"])
@login_required
def api_restaurants():
    """根據篩選條件返回符合的餐廳列表，並回傳可供前端使用的經緯度與評論資料。"""
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "無效的 JSON"}), 400

    # 提取篩選條件
    meal_types   = data.get("meal_types", []) or []
    categories   = data.get("categories", []) or []
    price_min    = data.get("price_min")
    price_max    = data.get("price_max")
    distance_limit = data.get("distance_limit")
    user_lat     = data.get("user_lat")
    user_lon     = data.get("user_lon")
    only_visited = bool(data.get("only_visited", False))

    # 開始查詢餐廳
    query = Restaurant.query

    # 如果用戶開啟飲控模式，只顯示健康餐廳
    if session.get("diet_mode"):
        query = query.filter_by(is_healthy=True)

    # ── 只顯示我記錄過的餐廳 ──────────────────────────────────────────────
    if only_visited:
        visited_names = [
            r[0] for r in db.session.query(Review.restaurant_name).distinct().filter(
                Review.user_id == session["user_id"]
            ).all()
        ]
        if not visited_names:
            return jsonify({"restaurants": [], "empty_reason": "no_records"})
        query = query.filter(Restaurant.name.in_(visited_names))

    # 根據餐別篩選（透過 restaurant_name 關聯）
    if meal_types:
        names = [r[0] for r in db.session.query(Review.restaurant_name).distinct().filter(
            Review.user_id == session["user_id"],
            Review.meal_type.in_(meal_types)
        ).all()]
        if names:
            query = query.filter(Restaurant.name.in_(names))
        else:
            return jsonify({"restaurants": []})
    
    # 根據料理類別篩選（前端選項直接對應 DB 的 cuisine_style 值）
    if categories:
        has_other = "其他" in categories
        real_styles = [c for c in categories if c != "其他"]
        conditions = []
        if real_styles:
            conditions.append(Restaurant.cuisine_style.in_(real_styles))
        if has_other:
            # 「其他」= cuisine_style 為 NULL 或不在任何已知值的
            known = db.session.query(Restaurant.cuisine_style).filter(
                Restaurant.cuisine_style.isnot(None)
            ).distinct().all()
            known_styles = [r[0] for r in known]
            conditions.append(
                db.or_(
                    Restaurant.cuisine_style == None,
                    ~Restaurant.cuisine_style.in_(known_styles)
                )
            )
        if conditions:
            query = query.filter(db.or_(*conditions))

    # 根據價位篩選
    if price_min is not None or price_max is not None:
        if price_min is not None and price_max is not None:
            query = query.filter(Restaurant.price_level.between(float(price_min), float(price_max)))
        elif price_min is not None:
            query = query.filter(Restaurant.price_level >= float(price_min))
        elif price_max is not None:
            query = query.filter(Restaurant.price_level <= float(price_max))

    restaurants = query.all()

    # 根據距離篩選（伺服器端地理編碼需要 GOOGLE_MAPS_API_KEY）
    filtered_restaurants = []
    if distance_limit and user_lat is not None and user_lon is not None:
        if not api_key:
            return jsonify({"error": "Server missing GOOGLE_MAPS_API_KEY for distance filtering"}), 500

        for restaurant in restaurants:
            if not restaurant.address:
                # 無地址的餐廳無法地理編碼，視為不納入距離計算，仍可視為符合條件
                continue
            try:
                params = {"address": restaurant.address, "key": api_key}
                geores = requests.get("https://maps.googleapis.com/maps/api/geocode/json", params=params, timeout=5)
                geodata = geores.json()
                if geodata.get("status") == "OK" and geodata.get("results"):
                    loc = geodata["results"][0]["geometry"]["location"]
                    lat = float(loc.get("lat"))
                    lng = float(loc.get("lng"))
                    dist_km = haversine_distance(user_lat, user_lon, lat, lng)
                    if dist_km <= float(distance_limit):
                        restaurant._geo_lat = lat
                        restaurant._geo_lng = lng
                        filtered_restaurants.append(restaurant)
                else:
                    continue
            except Exception:
                continue
    else:
        filtered_restaurants = restaurants

    # 組合回傳資料，包含 lat/lng（如果有）與 reviews
    result = []
    for restaurant in filtered_restaurants:
        reviews = Review.query.filter_by(restaurant_name=restaurant.name, user_id=session.get("user_id")).all()
        lat = getattr(restaurant, "_geo_lat", None)
        lng = getattr(restaurant, "_geo_lng", None)
        result.append({
            "id": restaurant.id,
            "name": restaurant.name,
            "area": restaurant.area,
            "address": restaurant.address,
            "category": restaurant.category,
            "cuisine_style": restaurant.cuisine_style,
            "price_level": restaurant.price_level,
            "is_healthy": restaurant.is_healthy,
            "lat": lat,
            "lng": lng,
            "reviews": [
                {
                    "id": r.id,
                    "meal_type": r.meal_type,
                    "rating": r.rating,
                    "comment": r.comment,
                    "visit_date": r.visit_date.isoformat() if r.visit_date else None,
                    "calories": r.calories,
                    "protein": r.protein,
                }
                for r in reviews
            ]
        })

    return jsonify({"restaurants": result})

@app.route("/api/diet_today", methods=["GET"])
@login_required
def api_diet_today():
    """獲取今天的飲食記錄和進度信息"""
    if not session.get("diet_mode"):
        return jsonify({"error": "飲控模式未啟用"}), 403
    
    # 獲取用戶的飲控設定
    diet_entry = UserDiet.query.filter_by(username=session["username"]).first()
    if not diet_entry:
        return jsonify({"error": "未找到飲控設定"}), 404
    
    # 獲取今天的飲食記錄
    today = date.today()
    today_reviews = Review.query.filter(
        Review.user_id == session["user_id"],
        Review.visit_date == today
    ).all()
    
    # 計算總熱量和蛋白質
    total_calories = sum(r.calories or 0 for r in today_reviews)
    total_protein = sum(r.protein or 0 for r in today_reviews)
    
    return jsonify({
        "tdee": diet_entry.TDEE,
        "protein_limit": diet_entry.protein_intake,
        "today_calories": total_calories,
        "today_protein": total_protein,
        "calories_percentage": round((total_calories / diet_entry.TDEE * 100) if diet_entry.TDEE else 0, 1),
        "protein_percentage": round((total_protein / diet_entry.protein_intake * 100) if diet_entry.protein_intake else 0, 1),
    })


# ── 飲控設定 ──────────────────────────────────────────────────────────────

ACTIVITY_OPTIONS = [
    (1.2, "無活動：久坐"),
    (1.375, "輕量活動：每週 1–3 天"),
    (1.55, "中度活動量：每週 3–5 天"),
    (1.725, "高度活動量：每週 6–7 天"),
    (1.9, "非常高度活動量：高強度勞力型"),
]


def calculate_diet_recommendation(gender, height, weight, age, activity_coeff, target_type):
    if gender not in ("男", "女"):
        return None

    if height is None or weight is None or age is None:
        return None

    if gender == "男":
        bmr = 13.7 * weight + 5.0 * height - 6.8 * age + 66
    else:
        bmr = 9.6 * weight + 1.8 * height - 4.7 * age + 655

    tdee = bmr * activity_coeff

    protein_factor = {
        "增肌": 1.6,
        "減脂": 2.0,
        "維持體重": 1.2,
    }.get(target_type, 1.2)
    protein_intake = weight * protein_factor

    return {
        "bmr": round(bmr, 1),
        "tdee": round(tdee, 1),
        "protein_intake": round(protein_intake, 1),
        "activity_coeff": activity_coeff,
        "target_type": target_type,
    }


@app.route("/diet_setting", methods=["GET", "POST"])
@login_required
def diet_setting():
    diet_entry = UserDiet.query.filter_by(username=session["username"]).first()
    form_data = {
        "diet_mode": bool(diet_entry and diet_entry.diet_mode) if diet_entry else False,
        "gender": diet_entry.gender if diet_entry and diet_entry.gender else "",
        "height": diet_entry.height if diet_entry and diet_entry.height is not None else "",
        "weight": diet_entry.weight if diet_entry and diet_entry.weight is not None else "",
        "age": diet_entry.age if diet_entry and diet_entry.age is not None else "",
        "activity_coeff": diet_entry.activity_coeff if diet_entry and diet_entry.activity_coeff is not None else "",
        "target_type": diet_entry.target_type if diet_entry and diet_entry.target_type else "維持體重",
    }
    recommendation = None

    if request.method == "POST":
        diet_mode = request.form.get("diet_mode") == "on"
        gender = request.form.get("gender", "").strip()
        height_str = request.form.get("height", "").strip()
        weight_str = request.form.get("weight", "").strip()
        age_str = request.form.get("age", "").strip()
        activity_coeff_str = request.form.get("activity_coeff", "").strip()
        target_type = request.form.get("target_type", "維持體重").strip()

        form_data.update({
            "diet_mode": diet_mode,
            "gender": gender,
            "height": height_str,
            "weight": weight_str,
            "age": age_str,
            "activity_coeff": activity_coeff_str,
            "target_type": target_type,
        })

        if diet_mode:
            errors = []
            try:
                height = float(height_str)
                if not 100 <= height <= 200:
                    errors.append("身高必須介於 100 到 200 公分。")
            except ValueError:
                errors.append("身高必須為浮點數。")

            try:
                weight = float(weight_str)
                if weight <= 10:
                    errors.append("體重必須大於 10 公斤。")
            except ValueError:
                errors.append("體重必須為浮點數。")

            try:
                age = int(age_str)
                if age <= 0:
                    errors.append("年齡必須為正整數。")
            except ValueError:
                errors.append("年齡必須為正整數。")

            if gender not in ("男", "女"):
                errors.append("請選擇性別。")

            try:
                activity_coeff = float(activity_coeff_str)
            except ValueError:
                activity_coeff = None
                errors.append("請選擇活動係數。")

            if target_type not in ("維持體重", "增肌", "減脂"):
                errors.append("請選擇飲控目的。")

            if errors:
                for msg in errors:
                    flash(msg, "danger")
            else:
                if diet_entry is None:
                    diet_entry = UserDiet(username=session["username"])
                    db.session.add(diet_entry)

                diet_entry.diet_mode = True
                diet_entry.gender = gender
                diet_entry.height = height
                diet_entry.weight = weight
                diet_entry.age = age
                diet_entry.activity_coeff = activity_coeff
                diet_entry.target_type = target_type
                recommendation = calculate_diet_recommendation(
                    gender=gender,
                    height=height,
                    weight=weight,
                    age=age,
                    activity_coeff=activity_coeff,
                    target_type=target_type,
                )
                if recommendation is not None:
                    diet_entry.TDEE = recommendation["tdee"]
                    diet_entry.protein_intake = recommendation["protein_intake"]
                db.session.commit()
                session["diet_mode"] = True
                flash("飲控模式已開啟並儲存。", "success")
        else:
            if diet_entry is None:
                diet_entry = UserDiet(username=session["username"])
                db.session.add(diet_entry)
            diet_entry.diet_mode = False
            db.session.commit()
            session["diet_mode"] = False
            flash("飲控模式已關閉，不會更動原有數值。", "info")

    return render_template(
        "diet_setting.html",
        diet_entry=diet_entry,
        form_data=form_data,
        recommendation=recommendation,
        activity_options=ACTIVITY_OPTIONS,
    )

# ---------------------------------------------------------------------------

# ── 餐廳資料庫 ────────────────────────────────────────────────────────────

@app.route("/restaurants")
@login_required
def restaurants():
    all_restaurants = (
        Restaurant.query
        .order_by(Restaurant.area, Restaurant.name)
        .all()
    )
    return render_template(
        "restaurants.html",
        restaurants=all_restaurants,
        current_user_id=session["user_id"],
    )


@app.route("/restaurants/new", methods=["POST"])
@login_required
def new_restaurant():
    name = request.form.get("name", "").strip()
    if not name:
        flash("餐廳名稱不可為空。", "danger")
        return redirect(url_for("restaurants"))

    if Restaurant.query.filter_by(name=name).first():
        flash(f"「{name}」已存在於資料庫中。", "warning")
        return redirect(url_for("restaurants"))

    restaurant = Restaurant(
        name=name,
        address=request.form.get("address", "").strip() or None,
        area=request.form.get("area", "").strip() or None,
        cuisine_style=request.form.get("cuisine_style", "").strip() or None,
        created_by=session["user_id"],
    )
    db.session.add(restaurant)
    db.session.commit()
    flash(f"「{name}」已成功加入餐廳資料庫！", "success")
    return redirect(url_for("restaurants"))


@app.route("/restaurants/<int:id>/delete", methods=["POST"])
@login_required
def delete_restaurant(id):
    restaurant = Restaurant.query.get_or_404(id)
    if restaurant.is_seeded:
        flash("系統預設餐廳不可刪除。", "danger")
        return redirect(url_for("restaurants"))
    db.session.delete(restaurant)
    db.session.commit()
    flash(f"「{restaurant.name}」已刪除。", "success")
    return redirect(url_for("restaurants"))


# ── API：菜單品項（供 new_review 的 JS 使用）────────────────────────────

@app.route("/api/menu")
def api_menu():
    name = request.args.get("restaurant", "").strip()
    if not name:
        return jsonify({"address": None, "items": []})
    restaurant = Restaurant.query.filter_by(name=name).first()
    if not restaurant:
        return jsonify({"address": None, "items": []})
    items = (
        MenuItem.query.filter_by(restaurant_id=restaurant.id)
        .order_by(MenuItem.item_name)
        .all()
    )
    def fmt_price(p):
        if p is None:
            return None
        return int(p) if p == int(p) else p
    return jsonify({
        "address": restaurant.address,
        "items": [
            {
                "item_name": item.item_name,
                "price": fmt_price(item.price),
                "calories": round(item.calories) if item.calories else None,
                "protein": round(item.protein, 1) if item.protein else None,
            }
            for item in items
        ],
    })


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
